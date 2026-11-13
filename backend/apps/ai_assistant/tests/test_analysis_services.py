import json
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.ai_assistant.models import (
    AIAnalysisRequest,
    AIAnalysisRequestEvidence,
    AIAnalysisRequestStatus,
    AIAnalysisRun,
    AIAnalysisStatus,
    AIProposal,
    AIProposalEvidence,
    AIProposalStatus,
    AIProposalType,
    AITask,
)
from apps.ai_assistant.services import (
    AIWorkspaceConflictError,
    AIWorkspaceNotFoundError,
    AIWorkspacePermissionError,
    apply_ai_proposal,
    claim_analysis_request,
    complete_analysis_request,
)
from apps.chat.models import Message
from apps.project_state.models import (
    EvidenceSourceType,
    OpenQuestion,
    ProjectConflict,
    Requirement,
)
from apps.project_state.services import resolve_ai_evidence_references
from apps.projects.models import ProjectMember
from apps.projects.services import create_project
from apps.questionnaire.models import QuestionnaireAnswer, QuestionnaireSubmission


@pytest.fixture
def ai_project_context():
    users = get_user_model()
    executor = users.objects.create_user(email="analysis-service-executor@example.com")
    customer = users.objects.create_user(email="analysis-service-customer@example.com")
    outsider = users.objects.create_user(email="analysis-service-outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "AI service project", "project_type": "other"},
    )
    ProjectMember.objects.create(
        project=project, user=customer, role="customer", status="active"
    )
    other_project = create_project(
        actor=outsider,
        data={"name": "Foreign AI project", "project_type": "other"},
    )
    return project, executor, customer, outsider, other_project


def _request_and_run(*, project, actor):
    request = AIAnalysisRequest.objects.create(project=project, requested_by=actor)
    run = AIAnalysisRun.objects.create(
        project=project,
        task_key=AITask.CONTRADICTION_DETECTION,
        trigger_type="manual",
        provider_key="test",
        model_name="test-model",
        profile_version=1,
        input_hash="a" * 64,
        status=AIAnalysisStatus.SUCCEEDED,
    )
    return request, run


def _proposal(*, project, actor, proposal_type, payload, evidence_refs=()):
    request, run = _request_and_run(project=project, actor=actor)
    if not evidence_refs:
        passport = project.passport
        snapshot = resolve_ai_evidence_references(
            project_id=project.pk,
            actor=actor,
            evidence_refs=[
                {
                    "source_type": EvidenceSourceType.PASSPORT,
                    "source_id": str(passport.pk),
                }
            ],
        )[(EvidenceSourceType.PASSPORT, passport.pk)]
        evidence_refs = (
            (
                snapshot["source_type"],
                snapshot["source_id"],
                snapshot["excerpt"],
                snapshot["metadata"],
            ),
        )
    evidence = [
        {
            "source_type": source_type,
            "source_id": source_id,
            "excerpt": excerpt,
            "metadata": metadata,
        }
        for source_type, source_id, excerpt, metadata in evidence_refs
    ]
    proposal = AIProposal.objects.create(
        project=project,
        analysis_run=run,
        analysis_request=request,
        idempotency_key="b" * 64,
        proposal_type=proposal_type,
        title="AI proposal",
        description="A reviewable suggestion.",
        rationale="The sources support this suggestion.",
        proposed_payload=payload,
    )
    AIProposalEvidence.objects.bulk_create(
        [AIProposalEvidence(proposal=proposal, **row) for row in evidence]
    )
    return proposal


@pytest.mark.django_db
def test_accepted_proposal_applies_once_through_project_state_service(
    ai_project_context,
):
    project, executor, _customer, _outsider, _other_project = ai_project_context
    proposal = _proposal(
        project=project,
        actor=executor,
        proposal_type=AIProposalType.REQUIREMENT_CREATE,
        payload={"title": "Encrypted backups", "description": "Daily backups."},
    )

    applied = apply_ai_proposal(proposal_id=proposal.pk, actor=executor)
    repeated = apply_ai_proposal(proposal_id=proposal.pk, actor=executor)

    assert applied.status == AIProposalStatus.APPLIED
    assert repeated.status == AIProposalStatus.APPLIED
    assert (
        Requirement.objects.filter(project=project, title="Encrypted backups").count()
        == 1
    )
    assert applied.reviewed_by_id == executor.pk
    assert applied.applied_at is not None


@pytest.mark.django_db
def test_failed_project_state_validation_leaves_proposal_pending(ai_project_context):
    project, executor, _customer, _outsider, _other_project = ai_project_context
    proposal = _proposal(
        project=project,
        actor=executor,
        proposal_type=AIProposalType.REQUIREMENT_CREATE,
        payload={"title": "Valid title", "description": ""},
    )

    with pytest.raises(ValidationError):
        apply_ai_proposal(
            proposal_id=proposal.pk,
            actor=executor,
            payload={"title": "Valid title", "unexpected": "invalid"},
        )

    proposal.refresh_from_db()
    assert proposal.status == AIProposalStatus.PENDING
    assert proposal.reviewed_by_id is None
    assert not Requirement.objects.filter(project=project).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("source_change", ["updated", "deleted"])
@pytest.mark.parametrize(
    "proposal_type,payload",
    [
        (
            AIProposalType.REQUIREMENT_CREATE,
            {"title": "Retain audit history", "description": "Keep changes."},
        ),
        (
            AIProposalType.OPEN_QUESTION_CREATE,
            {"question": "Which audit retention period is required?"},
        ),
    ],
)
def test_stale_evidence_blocks_non_conflict_proposal_application(
    ai_project_context, source_change, proposal_type, payload
):
    project, executor, _customer, _outsider, _other_project = ai_project_context
    proposal = _proposal(
        project=project,
        actor=executor,
        proposal_type=proposal_type,
        payload=payload,
    )
    passport = project.passport
    if source_change == "updated":
        passport.goal = "Changed after the analysis"
        passport.version += 1
        passport.save(update_fields=("goal", "version"))
    else:
        passport.delete()

    with pytest.raises(AIWorkspaceConflictError):
        apply_ai_proposal(proposal_id=proposal.pk, actor=executor)

    proposal.refresh_from_db()
    assert proposal.status == AIProposalStatus.PENDING
    assert proposal.reviewed_by_id is None
    assert proposal.applied_at is None
    assert not Requirement.objects.filter(project=project).exists()
    assert not OpenQuestion.objects.filter(project=project).exists()
    assert not ProjectConflict.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_conflict_preserves_both_sources_and_never_selects_a_winner(ai_project_context):
    project, executor, _customer, _outsider, _other_project = ai_project_context
    submission = QuestionnaireSubmission.objects.create(
        project=project,
        schema_key="other",
        schema_version=1,
        started_by=executor,
        submitted_by=executor,
        status="submitted",
    )
    first = QuestionnaireAnswer.objects.create(
        submission=submission,
        question_key="deadline",
        value="October",
        updated_by=executor,
    )
    second = QuestionnaireAnswer.objects.create(
        submission=submission,
        question_key="delivery_window",
        value="December",
        updated_by=executor,
    )
    source_refs = [
        {
            "source_type": EvidenceSourceType.QUESTIONNAIRE_ANSWER,
            "source_id": str(answer.pk),
        }
        for answer in (first, second)
    ]
    source_snapshots = resolve_ai_evidence_references(
        project_id=project.pk,
        actor=executor,
        evidence_refs=source_refs,
    )
    proposal = _proposal(
        project=project,
        actor=executor,
        proposal_type=AIProposalType.CONFLICT_CREATE,
        payload={"title": "Delivery timing differs", "description": "Values differ."},
        evidence_refs=(
            (
                EvidenceSourceType.QUESTIONNAIRE_ANSWER,
                first.pk,
                '"October"',
                source_snapshots[(EvidenceSourceType.QUESTIONNAIRE_ANSWER, first.pk)][
                    "metadata"
                ],
            ),
            (
                EvidenceSourceType.QUESTIONNAIRE_ANSWER,
                second.pk,
                '"December"',
                source_snapshots[(EvidenceSourceType.QUESTIONNAIRE_ANSWER, second.pk)][
                    "metadata"
                ],
            ),
        ),
    )

    applied = apply_ai_proposal(proposal_id=proposal.pk, actor=executor)

    conflict = ProjectConflict.objects.get(project=project)
    assert applied.status == AIProposalStatus.APPLIED
    assert conflict.evidence.count() == 2
    assert set(conflict.evidence.values_list("source_id", flat=True)) == {
        first.pk,
        second.pk,
    }
    assert set(conflict.evidence.values_list("excerpt", flat=True)) == {
        '"October"',
        '"December"',
    }
    assert conflict.resolution == ""


@pytest.mark.django_db
def test_customer_and_foreign_executor_cannot_apply_private_proposal(
    ai_project_context,
):
    project, executor, customer, outsider, _other_project = ai_project_context
    proposal = _proposal(
        project=project,
        actor=executor,
        proposal_type=AIProposalType.REQUIREMENT_CREATE,
        payload={"title": "Private suggestion", "description": ""},
    )

    with pytest.raises(AIWorkspacePermissionError):
        apply_ai_proposal(proposal_id=proposal.pk, actor=customer)
    with pytest.raises(AIWorkspaceNotFoundError):
        apply_ai_proposal(proposal_id=proposal.pk, actor=outsider)

    proposal.refresh_from_db()
    assert proposal.status == AIProposalStatus.PENDING
    assert not Requirement.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_expired_lease_fences_stale_worker_and_prevents_duplicate_proposals(
    ai_project_context,
):
    project, executor, _customer, _outsider, _other_project = ai_project_context
    request = AIAnalysisRequest.objects.create(project=project, requested_by=executor)
    queued, generation1, _ = claim_analysis_request(request_id=request.pk)
    busy, _same_generation, seconds_left = claim_analysis_request(request_id=request.pk)
    assert queued == "claimed"
    assert busy == "busy"
    assert seconds_left > 0

    AIAnalysisRequest.objects.filter(pk=request.pk).update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    reclaimed, generation2, _ = claim_analysis_request(request_id=request.pk)
    assert reclaimed == "claimed"
    assert generation2 == generation1 + 1

    passport = project.passport
    evidence = SimpleNamespace(
        source_type=EvidenceSourceType.PASSPORT,
        source_id=passport.pk,
        excerpt="Project goals",
        metadata={},
    )
    run = AIAnalysisRun.objects.create(
        project=project,
        task_key=AITask.CONTRADICTION_DETECTION,
        trigger_type="manual",
        provider_key="test",
        model_name="test-model",
        profile_version=1,
        input_hash="c" * 64,
        status=AIAnalysisStatus.SUCCEEDED,
    )
    response = SimpleNamespace(run_id=run.pk)
    candidate = {
        "proposal_type": AIProposalType.REQUIREMENT_CREATE,
        "title": "Requirement",
        "description": "Suggestion",
        "rationale": "Source supports it.",
        "payload": {"title": "Requirement", "description": ""},
        "evidence_keys": [(EvidenceSourceType.PASSPORT, str(passport.pk))],
    }
    evidence_by_key = {(EvidenceSourceType.PASSPORT, str(passport.pk)): evidence}

    assert not complete_analysis_request(
        request_id=request.pk,
        generation=generation1,
        response=response,
        proposals=[candidate],
        evidence_by_key=evidence_by_key,
    )
    assert complete_analysis_request(
        request_id=request.pk,
        generation=generation2,
        response=response,
        proposals=[candidate, candidate],
        evidence_by_key=evidence_by_key,
    )
    assert not complete_analysis_request(
        request_id=request.pk,
        generation=generation2,
        response=response,
        proposals=[candidate],
        evidence_by_key=evidence_by_key,
    )

    request.refresh_from_db()
    assert request.status == AIAnalysisRequestStatus.SUCCEEDED
    assert request.result_count == 1
    assert request.run_id == run.pk
    assert AIProposal.objects.filter(analysis_request=request).count() == 1


@pytest.mark.django_db
def test_analysis_uses_executor_scoped_source_snapshots_and_manual_router_contract(
    ai_project_context, monkeypatch
):
    from apps.ai_assistant import analysis

    project, executor, customer, _outsider, _other_project = ai_project_context
    submission = QuestionnaireSubmission.objects.create(
        project=project,
        schema_key="other",
        schema_version=1,
        started_by=customer,
        submitted_by=customer,
        status="submitted",
    )
    answer = QuestionnaireAnswer.objects.create(
        submission=submission,
        question_key="goal",
        value="Track inventory",
        updated_by=customer,
    )
    message = Message.objects.create(
        project=project,
        sender=customer,
        content="Please support barcode scans.",
        client_message_id=uuid4(),
    )
    request = AIAnalysisRequest.objects.create(
        project=project,
        requested_by=executor,
        status=AIAnalysisRequestStatus.RUNNING,
        execution_generation=1,
    )
    captured = {}
    fake_response = SimpleNamespace(parsed={"proposals": []}, run_id=None)

    def fake_generate_text(*, task_key, project_id, trigger_type, request):
        captured.update(
            task_key=task_key,
            project_id=project_id,
            trigger_type=trigger_type,
            generation_request=request,
        )
        return fake_response

    monkeypatch.setattr(analysis, "generate_text", fake_generate_text)
    response, proposals, evidence_by_key = analysis.run_project_analysis(
        request_id=request.pk,
        generation=1,
    )

    assert response is fake_response
    assert proposals == []
    assert captured["project_id"] == project.pk
    assert captured["task_key"] == AITask.CONTRADICTION_DETECTION
    assert captured["trigger_type"] == "manual"
    assert captured["generation_request"].prompt_version == "manual-project-analysis-v1"
    assert "untrusted" in captured["generation_request"].system_prompt
    assert len(captured["generation_request"].user_input.encode("utf-8")) <= 18_000
    assert (EvidenceSourceType.PASSPORT, str(project.passport.pk)) in evidence_by_key
    assert (EvidenceSourceType.QUESTIONNAIRE_ANSWER, str(answer.pk)) in evidence_by_key
    assert (EvidenceSourceType.MESSAGE, str(message.pk)) in evidence_by_key
    assert request.evidence_links.count() == 3
    assert all(row.request_id == request.pk for row in evidence_by_key.values())


@pytest.mark.django_db
def test_context_size_is_hard_capped_for_large_unicode_passport_and_state(
    ai_project_context,
):
    from apps.ai_assistant.analysis import (
        MAX_USER_CONTEXT_BYTES,
        _bounded_context,
    )

    project, executor, _customer, _outsider, _other_project = ai_project_context
    request = AIAnalysisRequest.objects.create(project=project, requested_by=executor)
    passport = project.passport
    passport_evidence = AIAnalysisRequestEvidence.objects.create(
        request=request,
        source_type=EvidenceSourceType.PASSPORT,
        source_id=passport.pk,
        excerpt="цель🧩" * 20_000,
        metadata={"sections": ["ограничения" * 10] * 30},
    )
    Requirement.objects.bulk_create(
        [
            Requirement(
                project=project,
                created_by=executor,
                title=f"Требование {index} " + "данные" * 40,
                description="подробное описание🧩" * 200,
            )
            for index in range(80)
        ]
    )

    encoded, included = _bounded_context(
        request=request,
        evidence_rows=[passport_evidence],
    )
    payload = json.loads(encoded)

    assert len(encoded.encode("utf-8")) <= MAX_USER_CONTEXT_BYTES
    assert payload["evidence"][0]["source_type"] == EvidenceSourceType.PASSPORT
    assert payload["evidence"][0]["source_id"] == str(passport.pk)
    assert payload["evidence"][0]["excerpt_truncated"] is True
    assert payload["evidence"][0]["metadata_truncated"] is True
    assert (
        EvidenceSourceType.PASSPORT,
        str(passport.pk),
    ) in included
    assert payload["project_state"]["requirements"]
    assert any(item["truncated"] for item in payload["project_state"]["requirements"])
    assert payload["context_limits"]["omitted_project_state_records"] > 0
    assert payload["context_limits"]["max_utf8_bytes"] == MAX_USER_CONTEXT_BYTES
    assert payload["context_limits"]["context_priority"]


@pytest.mark.django_db
def test_analysis_output_rejects_invalid_source_ids_and_single_source_conflicts():
    from apps.ai_assistant.analysis import _normalize_proposals

    key = (EvidenceSourceType.MESSAGE, "11111111-1111-1111-1111-111111111111")
    candidate = {
        "proposal_type": AIProposalType.CONFLICT_CREATE,
        "title": "Possible conflict",
        "description": "Two values differ.",
        "rationale": "The source statements do not agree.",
        "payload": {"title": "Possible conflict", "description": "Two values differ."},
        "evidence_refs": [
            {"source_type": EvidenceSourceType.MESSAGE, "source_id": key[1]}
        ],
    }

    with pytest.raises(ValueError, match="analysis_output_invalid"):
        _normalize_proposals(
            parsed={"proposals": [candidate]},
            evidence_by_key={key: object()},
        )

    candidate["evidence_refs"].append(
        {
            "source_type": EvidenceSourceType.MESSAGE,
            "source_id": "22222222-2222-2222-2222-222222222222",
        }
    )
    with pytest.raises(ValueError, match="analysis_output_invalid"):
        _normalize_proposals(
            parsed={"proposals": [candidate]},
            evidence_by_key={key: object()},
        )
