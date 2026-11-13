"""Executor-only analysis request and proposal lifecycle services."""

import hashlib
import json
import math
import re
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.project_state.selectors import get_project_member_role
from apps.project_state.services import (
    WRITEABLE_PROJECT_STATUSES,
    ProjectStateConflictError,
    ProjectStateNotFoundError,
    ProjectStatePermissionError,
    create_open_question,
    create_project_conflict,
    create_requirement,
    resolve_ai_evidence_references,
)
from apps.projects.models import Project, ProjectMemberRole

from .models import (
    AIAnalysisRequest,
    AIAnalysisRequestStatus,
    AIAnalysisRun,
    AIProposal,
    AIProposalEvidence,
    AIProposalStatus,
    AIProposalType,
    AITask,
)

ANALYSIS_LEASE = timedelta(minutes=6)
ERROR_CODE_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")


class AIWorkspaceNotFoundError(Exception):
    """A project or private AI record is outside the active member scope."""


class AIWorkspacePermissionError(Exception):
    """Only the active project executor can use the AI workspace."""


class AIWorkspaceConflictError(Exception):
    """The requested review action conflicts with the proposal state."""


def _authorize_executor(*, project_id, actor):
    role = get_project_member_role(project_id=project_id, actor=actor)
    if role is None:
        raise AIWorkspaceNotFoundError
    if role != ProjectMemberRole.EXECUTOR:
        raise AIWorkspacePermissionError


def queue_manual_analysis(*, project_id, actor, idempotency_key):
    request_id = uuid.uuid4()
    task_id = uuid.uuid4()
    with transaction.atomic():
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        if project is None:
            raise AIWorkspaceNotFoundError
        _authorize_executor(project_id=project_id, actor=actor)
        analysis_request = AIAnalysisRequest.objects.filter(
            project_id=project_id,
            requested_by=actor,
            idempotency_key=idempotency_key,
        ).first()
        created = analysis_request is None
        if created:
            if project.status not in WRITEABLE_PROJECT_STATUSES:
                raise AIWorkspaceConflictError
            analysis_request = AIAnalysisRequest.objects.create(
                id=request_id,
                celery_task_id=task_id,
                project_id=project_id,
                requested_by=actor,
                idempotency_key=idempotency_key,
            )
        if created:
            from .tasks import analyze_project

            transaction.on_commit(
                lambda rid=str(request_id), tid=str(task_id): _enqueue_analysis(
                    request_id=rid, task_id=tid, task=analyze_project
                )
            )
    analysis_request.refresh_from_db()
    return analysis_request


def _enqueue_analysis(*, request_id, task_id, task):
    try:
        task.apply_async(args=(request_id,), task_id=task_id)
    except Exception:
        AIAnalysisRequest.objects.filter(
            pk=request_id,
            celery_task_id=task_id,
            status=AIAnalysisRequestStatus.QUEUED,
        ).update(
            status=AIAnalysisRequestStatus.FAILED,
            error_code="queue_unavailable",
            completed_at=timezone.now(),
        )


def claim_analysis_request(*, request_id):
    now = timezone.now()
    with transaction.atomic():
        try:
            request = AIAnalysisRequest.objects.select_for_update().get(pk=request_id)
        except (AIAnalysisRequest.DoesNotExist, ValueError, TypeError):
            return "missing", None, 0
        if request.status in (
            AIAnalysisRequestStatus.SUCCEEDED,
            AIAnalysisRequestStatus.FAILED,
        ):
            return request.status, request.execution_generation, 0
        project = (
            Project.objects.select_for_update().filter(pk=request.project_id).first()
        )
        if project is None or project.status not in WRITEABLE_PROJECT_STATUSES:
            request.status = AIAnalysisRequestStatus.FAILED
            request.error_code = "project_read_only"
            request.completed_at = now
            request.lease_expires_at = None
            request.save(
                update_fields=(
                    "status",
                    "error_code",
                    "completed_at",
                    "lease_expires_at",
                )
            )
            return request.status, request.execution_generation, 0
        if (
            request.status == AIAnalysisRequestStatus.RUNNING
            and request.lease_expires_at is not None
            and request.lease_expires_at > now
        ):
            seconds_left = max(
                1, math.ceil((request.lease_expires_at - now).total_seconds())
            )
            return "busy", request.execution_generation, seconds_left
        request.status = AIAnalysisRequestStatus.RUNNING
        request.execution_generation += 1
        request.lease_expires_at = now + ANALYSIS_LEASE
        if request.started_at is None:
            request.started_at = now
        request.error_code = ""
        request.save(
            update_fields=(
                "status",
                "execution_generation",
                "lease_expires_at",
                "started_at",
                "error_code",
            )
        )
        return "claimed", request.execution_generation, ANALYSIS_LEASE.total_seconds()


def _safe_error_code(error):
    candidate = getattr(error, "code", "")
    if not candidate and isinstance(error, ValueError) and error.args:
        candidate = error.args[0]
    if isinstance(candidate, str) and ERROR_CODE_PATTERN.fullmatch(candidate):
        return candidate
    return "analysis_failed"


def fail_analysis_request(*, request_id, generation, error):
    with transaction.atomic():
        request = (
            AIAnalysisRequest.objects.select_for_update().filter(pk=request_id).first()
        )
        if (
            request is None
            or request.status != AIAnalysisRequestStatus.RUNNING
            or request.execution_generation != generation
        ):
            return False
        request.status = AIAnalysisRequestStatus.FAILED
        request.error_code = _safe_error_code(error)
        request.completed_at = timezone.now()
        request.lease_expires_at = None
        request.save(
            update_fields=("status", "error_code", "completed_at", "lease_expires_at")
        )
    return True


def _proposal_idempotency_key(*, proposal):
    canonical = json.dumps(
        {
            "proposal_type": proposal["proposal_type"],
            "title": proposal["title"],
            "payload": proposal["payload"],
            "evidence": sorted(
                [source_type, source_id]
                for source_type, source_id in proposal["evidence_keys"]
            ),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def complete_analysis_request(
    *, request_id, generation, response, proposals, evidence_by_key
):
    with transaction.atomic():
        request = AIAnalysisRequest.objects.select_for_update().get(pk=request_id)
        if (
            request.status != AIAnalysisRequestStatus.RUNNING
            or request.execution_generation != generation
        ):
            return False
        run = AIAnalysisRun.objects.filter(
            pk=response.run_id,
            project_id=request.project_id,
            task_key=AITask.CONTRADICTION_DETECTION,
        ).first()
        if run is None:
            raise ValueError("analysis_run_unavailable")

        seen_keys = set()
        proposal_count = 0
        for candidate in proposals:
            dedupe_key = _proposal_idempotency_key(proposal=candidate)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            proposal = AIProposal.objects.create(
                project_id=request.project_id,
                analysis_run=run,
                analysis_request=request,
                idempotency_key=dedupe_key,
                proposal_type=candidate["proposal_type"],
                title=candidate["title"],
                description=candidate["description"],
                rationale=candidate["rationale"],
                proposed_payload=candidate["payload"],
            )
            AIProposalEvidence.objects.bulk_create(
                [
                    AIProposalEvidence(
                        proposal=proposal,
                        source_type=evidence_by_key[source_key].source_type,
                        source_id=evidence_by_key[source_key].source_id,
                        excerpt=evidence_by_key[source_key].excerpt,
                        metadata=evidence_by_key[source_key].metadata,
                    )
                    for source_key in candidate["evidence_keys"]
                ]
            )
            proposal_count += 1

        request.run = run
        request.status = AIAnalysisRequestStatus.SUCCEEDED
        request.result_count = proposal_count
        request.completed_at = timezone.now()
        request.lease_expires_at = None
        request.save(
            update_fields=(
                "run",
                "status",
                "result_count",
                "completed_at",
                "lease_expires_at",
            )
        )
    return True


def list_analysis_requests(*, project_id, actor):
    _authorize_executor(project_id=project_id, actor=actor)
    return AIAnalysisRequest.objects.filter(project_id=project_id).select_related("run")


def get_analysis_request(*, project_id, request_id, actor):
    _authorize_executor(project_id=project_id, actor=actor)
    request = (
        AIAnalysisRequest.objects.filter(project_id=project_id, pk=request_id)
        .select_related("run")
        .first()
    )
    if request is None:
        raise AIWorkspaceNotFoundError
    return request


def list_ai_proposals(*, project_id, actor):
    _authorize_executor(project_id=project_id, actor=actor)
    return (
        AIProposal.objects.filter(project_id=project_id)
        .select_related("analysis_run", "reviewed_by")
        .prefetch_related("evidence_links")
    )


def get_ai_proposal(*, proposal_id, actor):
    proposal = (
        AIProposal.objects.filter(pk=proposal_id)
        .select_related("project", "analysis_run", "reviewed_by")
        .prefetch_related("evidence_links")
        .first()
    )
    if proposal is None:
        raise AIWorkspaceNotFoundError
    _authorize_executor(project_id=proposal.project_id, actor=actor)
    return proposal


def _proposal_state_data(*, proposal, payload):
    if proposal.proposal_type == AIProposalType.REQUIREMENT_CREATE:
        return create_requirement(
            project_id=proposal.project_id,
            actor=proposal.reviewed_by,
            data=payload,
        )
    if proposal.proposal_type == AIProposalType.OPEN_QUESTION_CREATE:
        return create_open_question(
            project_id=proposal.project_id,
            actor=proposal.reviewed_by,
            data=payload,
        )
    if proposal.proposal_type == AIProposalType.CONFLICT_CREATE:
        payload = dict(payload)
        payload["evidence_refs"] = [
            {
                "source_type": link.source_type,
                "source_id": str(link.source_id),
            }
            for link in proposal.evidence_links.all()
        ]
        expected_evidence = [
            {
                "source_type": link.source_type,
                "source_id": str(link.source_id),
                "excerpt": link.excerpt,
                "metadata": link.metadata,
            }
            for link in proposal.evidence_links.all()
        ]
        return create_project_conflict(
            project_id=proposal.project_id,
            actor=proposal.reviewed_by,
            data=payload,
            expected_evidence=expected_evidence,
        )
    raise ValidationError({"proposal_type": "This proposal type is unavailable."})


def _assert_proposal_evidence_current(*, proposal, actor):
    evidence_links = list(proposal.evidence_links.all())
    if not evidence_links:
        raise AIWorkspaceConflictError
    evidence_refs = [
        {"source_type": link.source_type, "source_id": str(link.source_id)}
        for link in evidence_links
    ]
    try:
        current_snapshots = resolve_ai_evidence_references(
            project_id=proposal.project_id,
            actor=actor,
            evidence_refs=evidence_refs,
        )
    except ProjectStateNotFoundError:
        # An evidence source removed since analysis makes the proposal stale.
        raise AIWorkspaceConflictError from None
    except (ProjectStateConflictError, ProjectStatePermissionError) as error:
        translate_project_state_error(error)

    for link in evidence_links:
        current = current_snapshots.get((link.source_type, link.source_id))
        if (
            current is None
            or current["excerpt"] != link.excerpt
            or current["metadata"] != link.metadata
        ):
            raise AIWorkspaceConflictError


def apply_ai_proposal(*, proposal_id, actor, payload=None):
    with transaction.atomic():
        proposal = (
            AIProposal.objects.select_for_update()
            .filter(pk=proposal_id)
            .prefetch_related("evidence_links")
            .first()
        )
        if proposal is None:
            raise AIWorkspaceNotFoundError
        _authorize_executor(project_id=proposal.project_id, actor=actor)
        if proposal.status == AIProposalStatus.APPLIED:
            if payload is None or payload == proposal.final_payload:
                return proposal
            raise AIWorkspaceConflictError
        if proposal.status != AIProposalStatus.PENDING:
            raise AIWorkspaceConflictError

        final_payload = proposal.proposed_payload if payload is None else payload
        _assert_proposal_evidence_current(proposal=proposal, actor=actor)
        proposal.reviewed_by = actor
        proposal.reviewed_at = timezone.now()
        try:
            _proposal_state_data(proposal=proposal, payload=final_payload)
        except (
            ProjectStateConflictError,
            ProjectStateNotFoundError,
            ProjectStatePermissionError,
        ) as error:
            translate_project_state_error(error)
        proposal.final_payload = final_payload
        proposal.status = AIProposalStatus.APPLIED
        proposal.applied_at = timezone.now()
        proposal.save(
            update_fields=(
                "reviewed_by",
                "reviewed_at",
                "final_payload",
                "status",
                "applied_at",
            )
        )
    return proposal


def reject_ai_proposal(*, proposal_id, actor):
    with transaction.atomic():
        proposal = AIProposal.objects.select_for_update().filter(pk=proposal_id).first()
        if proposal is None:
            raise AIWorkspaceNotFoundError
        _authorize_executor(project_id=proposal.project_id, actor=actor)
        if proposal.status == AIProposalStatus.REJECTED:
            return proposal
        if proposal.status != AIProposalStatus.PENDING:
            raise AIWorkspaceConflictError
        proposal.status = AIProposalStatus.REJECTED
        proposal.reviewed_by = actor
        proposal.reviewed_at = timezone.now()
        proposal.save(update_fields=("status", "reviewed_by", "reviewed_at"))
    return proposal


def translate_project_state_error(error):
    if isinstance(error, ProjectStateNotFoundError):
        raise AIWorkspaceNotFoundError from None
    if isinstance(error, ProjectStatePermissionError):
        raise AIWorkspacePermissionError from None
    if isinstance(error, ProjectStateConflictError):
        raise AIWorkspaceConflictError from None
    raise error
