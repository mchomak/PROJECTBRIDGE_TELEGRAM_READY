from datetime import timedelta
from uuid import uuid4

import pytest
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai_assistant.models import (
    AIAnalysisRequest,
    AIAnalysisRequestStatus,
    AIAnalysisRun,
    AIAnalysisStatus,
    AIProposal,
    AIProposalEvidence,
    AIProposalStatus,
    AIProposalType,
    AITask,
)
from apps.project_state.models import (
    EvidenceSourceType,
    OpenQuestion,
    ProjectConflict,
    Requirement,
)
from apps.project_state.services import resolve_ai_evidence_references
from apps.projects.models import ProjectMember, ProjectMemberStatus, ProjectStatus
from apps.projects.services import create_project


@pytest.mark.django_db
def test_executor_gets_durable_queue_id_and_customers_cannot_read_ai_history(
    monkeypatch,
):
    User = get_user_model()
    executor = User.objects.create_user(email="analysis-executor@example.com")
    customer = User.objects.create_user(email="analysis-customer@example.com")
    project = create_project(
        actor=executor, data={"name": "Analysis project", "project_type": "other"}
    )
    ProjectMember.objects.create(
        project=project, user=customer, role="customer", status="active"
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    from apps.ai_assistant import services, tasks

    enqueued = []

    def fake_enqueue(*, args, task_id):
        enqueued.append((args, task_id))

    monkeypatch.setattr(tasks.analyze_project, "apply_async", fake_enqueue)
    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert response.status_code == 202
    assert response.data["status"] == "queued"
    assert response.data["id"]
    queued = AIAnalysisRequest.objects.get(pk=response.data["id"])
    assert queued.status == AIAnalysisRequestStatus.QUEUED
    assert enqueued == [((str(queued.pk),), str(queued.celery_task_id))]
    replay = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(queued.idempotency_key),
    )
    assert replay.status_code == 202
    assert replay.data["id"] == response.data["id"]
    assert len(enqueued) == 1
    client.force_authenticate(user=customer)
    hidden_create = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    hidden = client.get(f"/api/v1/projects/{project.pk}/ai/analyses/")
    assert hidden_create.status_code == 403
    assert hidden.status_code == 403
    hidden_proposals = client.get(f"/api/v1/projects/{project.pk}/ai/proposals/")
    assert hidden_proposals.status_code == 403
    hidden_detail = client.get(
        f"/api/v1/projects/{project.pk}/ai/analyses/{queued.pk}/"
    )
    assert hidden_detail.status_code == 403
    assert AIAnalysisRequest.objects.filter(project=project).count() == 1
    assert len(enqueued) == 1


@pytest.mark.django_db
def test_beat_recovers_analysis_dispatch_lost_after_commit(monkeypatch):
    from apps.ai_assistant import services, tasks

    executor = get_user_model().objects.create_user(
        email="analysis-recovery@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Analysis recovery", "project_type": "other"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    monkeypatch.setattr(services.transaction, "on_commit", lambda _callback: None)

    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert response.status_code == 202
    request = AIAnalysisRequest.objects.get(pk=response.data["id"])
    assert request.status == AIAnalysisRequestStatus.QUEUED
    assert request.dispatch_attempts == 0
    AIAnalysisRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )
    dispatched = []
    monkeypatch.setattr(
        tasks.analyze_project,
        "apply_async",
        lambda *, args, task_id: dispatched.append((args, task_id)),
    )

    assert tasks.recover_stale_analysis_dispatches_task.run() == 1

    request.refresh_from_db()
    assert dispatched == [((str(request.pk),), str(request.celery_task_id))]
    assert request.dispatch_attempts == 1
    assert request.dispatch_lease_expires_at > timezone.now()


@pytest.mark.django_db
def test_successful_analysis_publishes_do_not_fence_a_delayed_worker(monkeypatch):
    from apps.ai_assistant import services, tasks

    executor = get_user_model().objects.create_user(
        email="analysis-backlog@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Analysis backlog", "project_type": "other"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    monkeypatch.setattr(services.transaction, "on_commit", lambda _callback: None)
    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    request = AIAnalysisRequest.objects.get(pk=response.data["id"])
    AIAnalysisRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    publications = []
    monkeypatch.setattr(
        tasks.analyze_project,
        "apply_async",
        lambda *, args, task_id: publications.append((args, task_id)),
    )
    for _ in range(7):
        AIAnalysisRequest.objects.filter(pk=request.pk).update(
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert tasks.recover_stale_analysis_dispatches_task.run() == 1

    request.refresh_from_db()
    assert request.status == AIAnalysisRequestStatus.QUEUED
    assert request.dispatch_attempts == 7
    assert request.error_code == "worker_backlog"
    assert publications == [((str(request.pk),), str(request.celery_task_id))] * 7

    def broker_unavailable(*, args, task_id):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(tasks.analyze_project, "apply_async", broker_unavailable)
    for _ in range(5):
        AIAnalysisRequest.objects.filter(pk=request.pk).update(
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert tasks.recover_stale_analysis_dispatches_task.run() == 0

    request.refresh_from_db()
    assert request.status == AIAnalysisRequestStatus.QUEUED
    assert request.execution_generation == 0
    assert request.dispatch_failures == 5

    monkeypatch.setattr(tasks, "run_project_analysis", lambda **_kwargs: None)
    assert tasks.analyze_project.run(*publications[0][0]) == "superseded"
    request.refresh_from_db()
    assert request.status == AIAnalysisRequestStatus.RUNNING
    assert request.execution_generation == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_beat_recovery_dispatches_analysis_once(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    from django.conf import settings
    from django.db import close_old_connections

    from apps.ai_assistant import services, tasks

    executor = get_user_model().objects.create_user(
        email="analysis-concurrent-recovery@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Concurrent analysis recovery", "project_type": "other"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    monkeypatch.setattr(services.transaction, "on_commit", lambda _callback: None)
    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    request = AIAnalysisRequest.objects.get(pk=response.data["id"])
    AIAnalysisRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    candidate_barrier = Barrier(2)
    dispatch_lock = Lock()
    dispatched = []
    real_candidates = services._stale_analysis_dispatch_candidates

    def synchronized_candidates():
        candidates = real_candidates()
        candidate_barrier.wait(timeout=10)
        return candidates

    def fake_apply_async(*, args, task_id):
        with dispatch_lock:
            dispatched.append((args, task_id))

    monkeypatch.setattr(
        services,
        "_stale_analysis_dispatch_candidates",
        synchronized_candidates,
    )
    monkeypatch.setattr(tasks.analyze_project, "apply_async", fake_apply_async)

    def recover():
        close_old_connections()
        try:
            return tasks.recover_stale_analysis_dispatches_task.run()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(recover) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]

    request.refresh_from_db()
    assert sorted(results) == [0, 1]
    assert dispatched == [((str(request.pk),), str(request.celery_task_id))]
    assert request.dispatch_attempts == 1
    assert request.dispatch_lease_expires_at > timezone.now()
    assert (
        settings.CELERY_BEAT_SCHEDULE["ai-analysis-dispatch-recovery"]["task"]
        == "apps.ai_assistant.tasks.recover_stale_analysis_dispatches_task"
    )


@pytest.mark.django_db
def test_ambiguous_analysis_publish_keeps_fifo_message_and_recovers(monkeypatch):
    from apps.ai_assistant import services, tasks

    executor = get_user_model().objects.create_user(
        email="analysis-exhaustion@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Analysis dispatch exhaustion", "project_type": "other"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    publish_calls = []

    def broker_unavailable(*, args, task_id):
        publish_calls.append((args, task_id))
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(tasks.analyze_project, "apply_async", broker_unavailable)
    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    request = AIAnalysisRequest.objects.get(pk=response.data["id"])
    assert response.status_code == 202
    assert request.status == AIAnalysisRequestStatus.QUEUED

    for _attempt in range(4):
        AIAnalysisRequest.objects.filter(pk=request.pk).update(
            created_at=timezone.now() - timedelta(days=1),
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1),
        )
        assert tasks.recover_stale_analysis_dispatches_task.run() == 0

    request.refresh_from_db()
    assert request.status == AIAnalysisRequestStatus.QUEUED
    assert request.error_code == "queue_unavailable"
    assert request.dispatch_attempts == 5
    assert len(publish_calls) == 5
    assert request.execution_generation == 0

    executions = []
    monkeypatch.setattr(
        tasks, "run_project_analysis", lambda **kwargs: executions.append(kwargs)
    )
    assert tasks.analyze_project.run(*publish_calls[0][0]) == "superseded"
    request.refresh_from_db()
    assert request.status == AIAnalysisRequestStatus.RUNNING
    assert request.execution_generation == 1
    assert request.error_code == ""
    assert len(executions) == 1
    with pytest.raises(Retry):
        tasks.analyze_project.run(*publish_calls[1][0])
    assert len(executions) == 1


@pytest.mark.django_db
def test_analysis_success_marker_save_failure_preserves_accepted_fifo(monkeypatch):
    from apps.ai_assistant import services, tasks

    executor = get_user_model().objects.create_user(
        email="analysis-marker-save@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Analysis accepted publish", "project_type": "other"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    real_success_marker = services._record_analysis_dispatch_success
    publications = []
    monkeypatch.setattr(
        tasks.analyze_project,
        "apply_async",
        lambda *, args, task_id: publications.append((args, task_id)),
    )

    def fail_success_marker(**_kwargs):
        raise OperationalError("temporary marker write failure")

    monkeypatch.setattr(
        services, "_record_analysis_dispatch_success", fail_success_marker
    )
    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    request = AIAnalysisRequest.objects.get(pk=response.data["id"])
    assert response.status_code == 202
    assert len(publications) == 1
    assert request.dispatch_successful_at is None

    AIAnalysisRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1),
        dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1),
    )
    monkeypatch.setattr(
        services, "_record_analysis_dispatch_success", real_success_marker
    )
    assert tasks.recover_stale_analysis_dispatches_task.run() == 1

    request.refresh_from_db()
    assert request.dispatch_successful_at is not None
    assert request.status == AIAnalysisRequestStatus.QUEUED
    assert request.execution_generation == 0
    assert publications == [
        ((str(request.pk),), str(request.celery_task_id)),
        ((str(request.pk),), str(request.celery_task_id)),
    ]
    executions = []
    monkeypatch.setattr(
        tasks, "run_project_analysis", lambda **kwargs: executions.append(kwargs)
    )
    assert tasks.analyze_project.run(*publications[0][0]) == "superseded"
    with pytest.raises(Retry):
        tasks.analyze_project.run(*publications[1][0])
    assert len(executions) == 1


@pytest.mark.django_db
def test_executor_cannot_enqueue_analysis_for_another_project():
    executor = get_user_model().objects.create_user(
        email="foreign-analysis@example.com"
    )
    create_project(
        actor=executor, data={"name": "Owned project", "project_type": "other"}
    )
    foreign_executor = get_user_model().objects.create_user(
        email="foreign-analysis-owner@example.com"
    )
    foreign_project = create_project(
        actor=foreign_executor,
        data={"name": "Foreign project", "project_type": "other"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{foreign_project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert response.status_code == 404
    assert not AIAnalysisRequest.objects.filter(project=foreign_project).exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "membership_status", [ProjectMemberStatus.LEFT, ProjectMemberStatus.REVOKED]
)
def test_inactive_executor_membership_cannot_start_analysis(membership_status):
    executor = get_user_model().objects.create_user(
        email=f"inactive-{membership_status}@example.com"
    )
    project = create_project(
        actor=executor, data={"name": "Inactive executor", "project_type": "other"}
    )
    membership = ProjectMember.objects.get(project=project, user=executor)
    membership.status = membership_status
    membership.save(update_fields=("status",))
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert response.status_code == 404
    assert not AIAnalysisRequest.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_queue_failure_keeps_durable_request_retryable_without_leaking_error(
    monkeypatch,
):
    executor = get_user_model().objects.create_user(email="queue-failure@example.com")
    project = create_project(
        actor=executor, data={"name": "Queue failure", "project_type": "other"}
    )
    key = str(uuid4())
    from apps.ai_assistant import services, tasks

    def fail_enqueue(*, args, task_id):
        raise RuntimeError("broker detail must not leak")

    monkeypatch.setattr(tasks.analyze_project, "apply_async", fail_enqueue)
    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )

    assert response.status_code == 202
    queued = AIAnalysisRequest.objects.get(pk=response.data["id"])
    assert queued.status == AIAnalysisRequestStatus.QUEUED
    assert queued.dispatch_attempts == 1
    assert queued.dispatch_lease_expires_at > timezone.now()
    assert "broker detail" not in str(response.data)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "project_status", [ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED]
)
def test_read_only_project_cannot_start_analysis(project_status):
    executor = get_user_model().objects.create_user(
        email=f"read-only-{project_status}@example.com"
    )
    project = create_project(
        actor=executor, data={"name": "Read only", "project_type": "other"}
    )
    project.status = project_status
    project.status_before_archive = (
        ProjectStatus.ACTIVE if project_status == ProjectStatus.ARCHIVED else None
    )
    project.archived_at = (
        timezone.now() if project_status == ProjectStatus.ARCHIVED else None
    )
    project.save(update_fields=("status", "status_before_archive", "archived_at"))
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{project.pk}/ai/analyses/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert response.status_code == 409
    assert not AIAnalysisRequest.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_queued_analysis_closed_before_worker_claim_fails_without_router_call(
    monkeypatch,
):
    from apps.ai_assistant import tasks

    executor = get_user_model().objects.create_user(
        email="close-after-queue@example.com"
    )
    project = create_project(
        actor=executor, data={"name": "Close after queue", "project_type": "other"}
    )
    analysis_request = AIAnalysisRequest.objects.create(
        project=project,
        requested_by=executor,
    )
    project.status = ProjectStatus.COMPLETED
    project.save(update_fields=("status",))
    monkeypatch.setattr(
        tasks,
        "run_project_analysis",
        lambda **kwargs: pytest.fail("closed projects must not call AI analysis"),
    )

    result = tasks.analyze_project.apply(args=(str(analysis_request.pk),)).get()

    analysis_request.refresh_from_db()
    assert result == "failed"
    assert analysis_request.status == AIAnalysisRequestStatus.FAILED
    assert analysis_request.error_code == "project_read_only"
    assert analysis_request.run_id is None


def _create_requirement_proposal(
    *,
    project,
    actor,
    proposal_type=AIProposalType.REQUIREMENT_CREATE,
    payload=None,
):
    analysis_request = AIAnalysisRequest.objects.create(
        project=project,
        requested_by=actor,
    )
    run = AIAnalysisRun.objects.create(
        project=project,
        task_key=AITask.CONTRADICTION_DETECTION,
        trigger_type="manual",
        provider_key="test",
        model_name="test-model",
        profile_version=1,
        input_hash="d" * 64,
        status=AIAnalysisStatus.SUCCEEDED,
    )
    proposal = AIProposal.objects.create(
        project=project,
        analysis_run=run,
        analysis_request=analysis_request,
        idempotency_key="e" * 64,
        proposal_type=proposal_type,
        title="Add an audit trail",
        description="A proposed requirement.",
        rationale="Project evidence indicates this is needed.",
        proposed_payload=payload
        or {"title": "Audit trail", "description": "Record changes."},
    )
    snapshot = resolve_ai_evidence_references(
        project_id=project.pk,
        actor=actor,
        evidence_refs=[
            {
                "source_type": EvidenceSourceType.PASSPORT,
                "source_id": str(project.passport.pk),
            }
        ],
    )[(EvidenceSourceType.PASSPORT, project.passport.pk)]
    AIProposalEvidence.objects.create(
        proposal=proposal,
        source_type=snapshot["source_type"],
        source_id=snapshot["source_id"],
        excerpt=snapshot["excerpt"],
        metadata=snapshot["metadata"],
    )
    return proposal


@pytest.mark.django_db
def test_proposal_rest_is_private_and_accept_is_idempotent():
    User = get_user_model()
    executor = User.objects.create_user(email="proposal-api-executor@example.com")
    customer = User.objects.create_user(email="proposal-api-customer@example.com")
    project = create_project(
        actor=executor, data={"name": "Proposal API", "project_type": "other"}
    )
    ProjectMember.objects.create(
        project=project, user=customer, role="customer", status="active"
    )
    proposal = _create_requirement_proposal(project=project, actor=executor)
    client = APIClient()

    client.force_authenticate(user=customer)
    hidden_detail = client.get(f"/api/v1/ai/proposals/{proposal.pk}/")
    hidden_accept = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/accept/", {}, format="json"
    )
    hidden_reject = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/reject/", {}, format="json"
    )
    hidden_apply_edited = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/apply-edited/",
        {
            "final_payload": {
                "title": "Customer must not apply this",
                "description": "Customer cannot edit private proposals.",
            }
        },
        format="json",
    )
    assert hidden_detail.status_code == 403
    assert hidden_accept.status_code == 403
    assert hidden_reject.status_code == 403
    assert hidden_apply_edited.status_code == 403
    proposal.refresh_from_db()
    assert proposal.status == AIProposalStatus.PENDING
    assert proposal.reviewed_by_id is None
    assert not Requirement.objects.filter(project=project).exists()

    client.force_authenticate(user=executor)
    detail = client.get(f"/api/v1/ai/proposals/{proposal.pk}/")
    accepted = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/accept/", {}, format="json"
    )
    repeated = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/accept/", {}, format="json"
    )
    assert detail.status_code == 200
    assert detail.data["evidence"][0]["source_type"] == "passport"
    assert accepted.status_code == 200
    assert accepted.data["status"] == AIProposalStatus.APPLIED
    assert repeated.data["status"] == AIProposalStatus.APPLIED
    assert Requirement.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_edit_validation_failure_stays_pending_and_executor_can_reject():
    executor = get_user_model().objects.create_user(email="proposal-review@example.com")
    project = create_project(
        actor=executor, data={"name": "Proposal review", "project_type": "other"}
    )
    proposal = _create_requirement_proposal(project=project, actor=executor)
    client = APIClient()
    client.force_authenticate(user=executor)

    invalid = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/apply-edited/",
        {"final_payload": {"title": "Edited", "unknown": "reject"}},
        format="json",
    )
    proposal.refresh_from_db()
    assert invalid.status_code == 400
    assert proposal.status == AIProposalStatus.PENDING
    assert not Requirement.objects.filter(project=project).exists()

    rejected = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/reject/", {}, format="json"
    )
    assert rejected.status_code == 200
    assert rejected.data["status"] == AIProposalStatus.REJECTED
    assert Requirement.objects.filter(project=project).count() == 0


@pytest.mark.django_db
def test_executor_can_edit_and_apply_proposal():
    executor = get_user_model().objects.create_user(email="proposal-edit@example.com")
    project = create_project(
        actor=executor, data={"name": "Edited proposal", "project_type": "other"}
    )
    proposal = _create_requirement_proposal(project=project, actor=executor)
    client = APIClient()
    client.force_authenticate(user=executor)

    applied = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/apply-edited/",
        {
            "final_payload": {
                "title": "Executor edited title",
                "description": "Executor approved wording.",
            }
        },
        format="json",
    )

    assert applied.status_code == 200
    assert applied.data["status"] == AIProposalStatus.APPLIED
    assert applied.data["final_payload"] == {
        "title": "Executor edited title",
        "description": "Executor approved wording.",
    }
    assert Requirement.objects.get(project=project).title == "Executor edited title"


@pytest.mark.django_db
@pytest.mark.parametrize("source_change", ["updated", "deleted"])
@pytest.mark.parametrize(
    "proposal_type,payload",
    [
        (
            AIProposalType.REQUIREMENT_CREATE,
            {"title": "Audit trail", "description": "Record changes."},
        ),
        (
            AIProposalType.OPEN_QUESTION_CREATE,
            {"question": "Which audit retention period is required?"},
        ),
    ],
)
def test_api_keeps_proposal_pending_when_evidence_is_stale(
    source_change, proposal_type, payload
):
    executor = get_user_model().objects.create_user(
        email=f"stale-evidence-{source_change}@example.com"
    )
    project = create_project(
        actor=executor, data={"name": "Stale evidence", "project_type": "other"}
    )
    proposal = _create_requirement_proposal(
        project=project,
        actor=executor,
        proposal_type=proposal_type,
        payload=payload,
    )
    passport = project.passport
    if source_change == "updated":
        passport.goal = "Changed after analysis"
        passport.version += 1
        passport.save(update_fields=("goal", "version"))
    else:
        passport.delete()

    client = APIClient()
    client.force_authenticate(user=executor)
    response = client.post(
        f"/api/v1/ai/proposals/{proposal.pk}/accept/", {}, format="json"
    )

    proposal.refresh_from_db()
    assert response.status_code == 409
    assert proposal.status == AIProposalStatus.PENDING
    assert proposal.reviewed_by_id is None
    assert proposal.applied_at is None
    assert not Requirement.objects.filter(project=project).exists()
    assert not OpenQuestion.objects.filter(project=project).exists()
    assert not ProjectConflict.objects.filter(project=project).exists()
