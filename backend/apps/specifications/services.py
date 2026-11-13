"""Specification access, editing, and generation request services."""

import hashlib
import json
import math
import re
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.project_state.selectors import get_project_member_role
from apps.project_state.services import WRITEABLE_PROJECT_STATUSES
from apps.projects.models import (
    Project,
    ProjectMemberRole,
)
from apps.projects.selectors import get_project_for_member

from .models import (
    Specification,
    SpecificationGenerationRequest,
    SpecificationGenerationStatus,
    SpecificationStatus,
)
from .selectors import (
    get_latest_generation_for_member,
    get_specification_generation_context,
)

GENERATION_LEASE = timedelta(minutes=6)
GENERATION_DISPATCH_STALE_AFTER = timedelta(minutes=1)
GENERATION_DISPATCH_LEASE = timedelta(minutes=2)
GENERATION_DISPATCH_RETRY_BASE = timedelta(seconds=30)
GENERATION_DISPATCH_RETRY_MAX = timedelta(minutes=30)
GENERATION_DISPATCH_UNAVAILABLE_AFTER = 5
GENERATION_DISPATCH_BACKLOG_WARNING_AFTER = 5
MAX_GENERATION_DISPATCH_FAILURES = 12
GENERATION_DISPATCH_BATCH_SIZE = 100
MAX_MARKDOWN_LENGTH = 100_000
ERROR_CODE_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")


class SpecificationNotFoundError(Exception):
    """The specification is unavailable to the active project member."""


class SpecificationPermissionError(Exception):
    """Only the executor can generate or edit a specification."""


class SpecificationConflictError(Exception):
    """The requested operation conflicts with the current specification."""


class SpecificationGenerationContextTooLargeError(Exception):
    """The approved context exceeds the worker's UTF-8 input budget."""

    code = "source_context_too_large"


def hash_source_context(context):
    canonical = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _authorize_project(*, project_id, actor, executor_only=False):
    role = get_project_member_role(project_id=project_id, actor=actor)
    if role is None:
        raise SpecificationNotFoundError
    if executor_only and role != ProjectMemberRole.EXECUTOR:
        raise SpecificationPermissionError
    return role


def _get_specification(*, project, actor, lock=False):
    manager = (
        Specification.objects.select_for_update() if lock else Specification.objects
    )
    specification, _ = manager.get_or_create(
        project=project,
        defaults={"updated_by": project.created_by},
    )
    return specification


def get_specification(*, project_id, actor):
    project = get_project_for_member(project_id=project_id, user=actor)
    if project is None:
        raise SpecificationNotFoundError
    return _get_specification(project=project, actor=actor)


def get_latest_generation(*, project_id, actor):
    role = _authorize_project(project_id=project_id, actor=actor)
    if role != ProjectMemberRole.EXECUTOR:
        return None
    return get_latest_generation_for_member(project_id=project_id, actor=actor)


def update_specification(*, project_id, actor, content, expected_version):
    if not isinstance(content, str):
        raise ValidationError({"content": "Provide Markdown text."})
    if len(content) > MAX_MARKDOWN_LENGTH:
        raise ValidationError(
            {"content": f"Markdown must be {MAX_MARKDOWN_LENGTH} characters or fewer."}
        )
    if isinstance(expected_version, bool) or not isinstance(expected_version, int):
        raise ValidationError({"version": "Provide the current specification version."})

    with transaction.atomic():
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        if project is None:
            raise SpecificationNotFoundError
        _authorize_project(project_id=project_id, actor=actor, executor_only=True)
        specification = _get_specification(project=project, actor=actor, lock=True)
        if project.status not in WRITEABLE_PROJECT_STATUSES:
            raise SpecificationConflictError
        if specification.version != expected_version:
            raise SpecificationVersionConflictError

        now = timezone.now()
        SpecificationGenerationRequest.objects.filter(
            project_id=project_id,
            status__in=(
                SpecificationGenerationStatus.QUEUED,
                SpecificationGenerationStatus.RUNNING,
            ),
        ).update(
            status=SpecificationGenerationStatus.SUPERSEDED,
            execution_generation=F("execution_generation") + 1,
            lease_expires_at=None,
            dispatch_lease_expires_at=None,
            completed_at=now,
            error_code="draft_edited",
        )
        specification.content = content
        specification.status = SpecificationStatus.DRAFT
        specification.updated_by = actor
        specification.version += 1
        specification.save(
            update_fields=("content", "status", "updated_by", "version", "updated_at")
        )
    return specification


def queue_specification_generation(*, project_id, actor, idempotency_key):
    task_id = uuid.uuid4()
    request_id = uuid.uuid4()
    with transaction.atomic():
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        if project is None:
            raise SpecificationNotFoundError
        _authorize_project(project_id=project_id, actor=actor, executor_only=True)
        existing = SpecificationGenerationRequest.objects.filter(
            project_id=project_id,
            requested_by=actor,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            return existing
        if project.status not in WRITEABLE_PROJECT_STATUSES:
            raise SpecificationConflictError
        specification = _get_specification(project=project, actor=actor, lock=True)
        if SpecificationGenerationRequest.objects.filter(
            project_id=project_id,
            status__in=(
                SpecificationGenerationStatus.QUEUED,
                SpecificationGenerationStatus.RUNNING,
            ),
        ).exists():
            raise SpecificationConflictError

        context = get_specification_generation_context(project=project, actor=actor)
        request = SpecificationGenerationRequest.objects.create(
            id=request_id,
            project=project,
            specification=specification,
            requested_by=actor,
            idempotency_key=idempotency_key,
            expected_version=specification.version,
            source_context_hash=hash_source_context(context),
            celery_task_id=task_id,
        )
        from .tasks import generate_specification

        transaction.on_commit(
            lambda rid=str(request_id), tid=str(task_id): _enqueue_generation(
                request_id=rid,
                task_id=tid,
                task=generate_specification,
            )
        )
    request.refresh_from_db()
    return request


class SpecificationVersionConflictError(SpecificationConflictError):
    """The editable draft has advanced since it was loaded."""


def _enqueue_generation(*, request_id, task_id, task, require_stale=False):
    attempt = _reserve_generation_dispatch(
        request_id=request_id,
        task_id=task_id,
        require_stale=require_stale,
    )
    if attempt is None:
        return False
    try:
        task.apply_async(args=(request_id,), task_id=task_id)
    except Exception:
        try:
            _record_generation_dispatch_failure(
                request_id=request_id,
                task_id=task_id,
                attempt=attempt,
            )
        except Exception:
            # The durable dispatch lease will expire and Beat will recover it.
            pass
        return False
    try:
        _record_generation_dispatch_success(
            request_id=request_id,
            task_id=task_id,
            attempt=attempt,
        )
    except Exception:
        # A successful publish remains recoverable if its outcome marker cannot save.
        pass
    return True


def _reserve_generation_dispatch(*, request_id, task_id, require_stale):
    now = timezone.now()
    with transaction.atomic():
        request = (
            SpecificationGenerationRequest.objects.select_for_update()
            .filter(pk=request_id, celery_task_id=task_id)
            .first()
        )
        if request is None or request.status != SpecificationGenerationStatus.QUEUED:
            return None
        if require_stale and request.created_at > now - GENERATION_DISPATCH_STALE_AFTER:
            return None
        if (
            request.dispatch_lease_expires_at is not None
            and request.dispatch_lease_expires_at > now
        ):
            return None
        if (
            request.dispatch_successful_at is None
            and request.dispatch_attempts > request.dispatch_failures
        ):
            # An expired reservation without a recorded broker error is ambiguous.
            request.dispatch_successful_at = now
            if request.dispatch_attempts >= GENERATION_DISPATCH_BACKLOG_WARNING_AFTER:
                request.error_code = "worker_backlog"
        request.dispatch_attempts += 1
        request.dispatch_lease_expires_at = now + GENERATION_DISPATCH_LEASE
        request.save(
            update_fields=(
                "dispatch_attempts",
                "dispatch_lease_expires_at",
                "dispatch_successful_at",
                "error_code",
            )
        )
        return request.dispatch_attempts


def _record_generation_dispatch_success(*, request_id, task_id, attempt):
    with transaction.atomic():
        request = (
            SpecificationGenerationRequest.objects.select_for_update()
            .filter(
                pk=request_id,
                celery_task_id=task_id,
                status=SpecificationGenerationStatus.QUEUED,
                dispatch_attempts=attempt,
            )
            .first()
        )
        if request is None:
            return
        fields = []
        if request.dispatch_successful_at is None:
            request.dispatch_successful_at = timezone.now()
            fields.append("dispatch_successful_at")
        if request.dispatch_failures:
            request.dispatch_failures = 0
            fields.append("dispatch_failures")
        if request.dispatch_attempts >= GENERATION_DISPATCH_BACKLOG_WARNING_AFTER:
            request.error_code = "worker_backlog"
            fields.append("error_code")
        elif request.error_code in {"queue_unavailable", "worker_backlog"}:
            request.error_code = ""
            fields.append("error_code")
        if fields:
            request.save(update_fields=tuple(fields))


def _record_generation_dispatch_failure(*, request_id, task_id, attempt):
    now = timezone.now()
    with transaction.atomic():
        request = (
            SpecificationGenerationRequest.objects.select_for_update()
            .filter(
                pk=request_id,
                celery_task_id=task_id,
                status=SpecificationGenerationStatus.QUEUED,
                dispatch_attempts=attempt,
            )
            .first()
        )
        if request is None:
            return
        request.dispatch_failures = min(
            MAX_GENERATION_DISPATCH_FAILURES, request.dispatch_failures + 1
        )
        if request.dispatch_failures >= GENERATION_DISPATCH_UNAVAILABLE_AFTER:
            request.error_code = "queue_unavailable"
        delay = _generation_dispatch_retry_delay(request.dispatch_failures)
        request.dispatch_lease_expires_at = now + delay
        request.save(
            update_fields=(
                "error_code",
                "dispatch_failures",
                "dispatch_lease_expires_at",
            )
        )


def _generation_dispatch_retry_delay(failures):
    multiplier = 2 ** max(0, min(failures - 1, 10))
    return min(
        GENERATION_DISPATCH_RETRY_BASE * multiplier, GENERATION_DISPATCH_RETRY_MAX
    )


def _stale_generation_dispatch_candidates(*, now=None):
    now = now or timezone.now()
    stale_before = now - GENERATION_DISPATCH_STALE_AFTER
    return list(
        SpecificationGenerationRequest.objects.filter(
            status=SpecificationGenerationStatus.QUEUED,
            created_at__lte=stale_before,
        )
        .filter(
            Q(dispatch_lease_expires_at__isnull=True)
            | Q(dispatch_lease_expires_at__lte=now)
        )
        .order_by("created_at", "id")
        .values_list("id", "celery_task_id")[:GENERATION_DISPATCH_BATCH_SIZE]
    )


def recover_stale_specification_generation_dispatches():
    candidates = _stale_generation_dispatch_candidates()
    from .tasks import generate_specification

    dispatched = 0
    for request_id, task_id in candidates:
        if _enqueue_generation(
            request_id=str(request_id),
            task_id=str(task_id),
            task=generate_specification,
            require_stale=True,
        ):
            dispatched += 1
    return dispatched


def _safe_error_code(error):
    candidate = getattr(error, "code", "")
    if not candidate and isinstance(error, ValueError) and error.args:
        candidate = error.args[0]
    if isinstance(candidate, str) and ERROR_CODE_PATTERN.fullmatch(candidate):
        return candidate
    return "generation_failed"


def _finish_request(request, *, status, error_code=""):
    request.status = status
    request.error_code = error_code
    request.completed_at = timezone.now()
    request.lease_expires_at = None
    request.dispatch_lease_expires_at = None
    request.save(
        update_fields=(
            "status",
            "error_code",
            "completed_at",
            "lease_expires_at",
            "dispatch_lease_expires_at",
            "dispatch_failures",
        )
    )


def claim_generation_request(*, request_id):
    now = timezone.now()
    with transaction.atomic():
        try:
            project_id = SpecificationGenerationRequest.objects.values_list(
                "project_id", flat=True
            ).get(pk=request_id)
        except (SpecificationGenerationRequest.DoesNotExist, ValueError, TypeError):
            return "missing", None, 0, None, None
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        try:
            request = (
                SpecificationGenerationRequest.objects.select_for_update()
                .select_related("requested_by", "specification")
                .get(pk=request_id)
            )
        except (SpecificationGenerationRequest.DoesNotExist, ValueError, TypeError):
            return "missing", None, 0, None, None

        if request.status in (
            SpecificationGenerationStatus.SUCCEEDED,
            SpecificationGenerationStatus.FAILED,
            SpecificationGenerationStatus.SUPERSEDED,
        ):
            return request.status, request.execution_generation, 0, None, None

        specification = (
            Specification.objects.select_for_update()
            .filter(pk=request.specification_id)
            .first()
        )
        if project is None or specification is None:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.FAILED,
                error_code="project_unavailable",
            )
            return request.status, request.execution_generation, 0, None, None
        if project.status not in WRITEABLE_PROJECT_STATUSES:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.FAILED,
                error_code="project_read_only",
            )
            return request.status, request.execution_generation, 0, None, None
        if specification.version != request.expected_version:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.SUPERSEDED,
                error_code="draft_edited",
            )
            return request.status, request.execution_generation, 0, None, None
        if (
            request.status == SpecificationGenerationStatus.RUNNING
            and request.lease_expires_at is not None
            and request.lease_expires_at > now
        ):
            seconds_left = max(
                1, math.ceil((request.lease_expires_at - now).total_seconds())
            )
            return "busy", request.execution_generation, seconds_left, None, None

        role = get_project_member_role(
            project_id=project.pk, actor=request.requested_by
        )
        if role != ProjectMemberRole.EXECUTOR:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.FAILED,
                error_code="requester_not_active_executor",
            )
            return request.status, request.execution_generation, 0, None, None

        context = get_specification_generation_context(
            project=project,
            actor=request.requested_by,
        )
        if hash_source_context(context) != request.source_context_hash:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.SUPERSEDED,
                error_code="sources_changed",
            )
            return request.status, request.execution_generation, 0, None, None

        request.status = SpecificationGenerationStatus.RUNNING
        request.dispatch_attempts = 0
        request.dispatch_failures = 0
        request.execution_generation += 1
        request.lease_expires_at = now + GENERATION_LEASE
        request.dispatch_lease_expires_at = None
        request.dispatch_successful_at = None
        if request.started_at is None:
            request.started_at = now
        request.error_code = ""
        request.save(
            update_fields=(
                "status",
                "dispatch_attempts",
                "execution_generation",
                "lease_expires_at",
                "dispatch_lease_expires_at",
                "dispatch_successful_at",
                "dispatch_failures",
                "started_at",
                "error_code",
            )
        )
        return (
            "claimed",
            request.execution_generation,
            GENERATION_LEASE.total_seconds(),
            project.pk,
            context,
        )


def generation_request_matches_current_sources(*, request_id, generation):
    """Fence source changes after claiming and just before a provider call."""
    with transaction.atomic():
        try:
            project_id = SpecificationGenerationRequest.objects.values_list(
                "project_id", flat=True
            ).get(pk=request_id)
        except (SpecificationGenerationRequest.DoesNotExist, ValueError, TypeError):
            return False

        project = Project.objects.select_for_update().filter(pk=project_id).first()
        request = (
            SpecificationGenerationRequest.objects.select_for_update()
            .select_related("requested_by")
            .filter(pk=request_id)
            .first()
        )
        if (
            request is None
            or request.status != SpecificationGenerationStatus.RUNNING
            or request.execution_generation != generation
        ):
            return False
        specification = (
            Specification.objects.select_for_update()
            .filter(pk=request.specification_id)
            .first()
        )
        if project is None or specification is None:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.FAILED,
                error_code="project_unavailable",
            )
            return False
        if (
            project.status not in WRITEABLE_PROJECT_STATUSES
            or specification.version != request.expected_version
            or get_project_member_role(
                project_id=project.pk,
                actor=request.requested_by,
            )
            != ProjectMemberRole.EXECUTOR
        ):
            _finish_request(
                request,
                status=SpecificationGenerationStatus.SUPERSEDED,
                error_code="draft_or_project_changed",
            )
            return False

        context = get_specification_generation_context(
            project=project,
            actor=request.requested_by,
        )
        if hash_source_context(context) != request.source_context_hash:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.SUPERSEDED,
                error_code="sources_changed",
            )
            return False
    return True


def complete_generation_request(*, request_id, generation, content):
    if not isinstance(content, str) or not content.strip():
        return fail_generation_request(
            request_id=request_id,
            generation=generation,
            error=ValueError("generation_output_empty"),
        )
    if len(content) > MAX_MARKDOWN_LENGTH:
        return fail_generation_request(
            request_id=request_id,
            generation=generation,
            error=ValueError("generation_output_too_large"),
        )

    with transaction.atomic():
        try:
            project_id = SpecificationGenerationRequest.objects.values_list(
                "project_id", flat=True
            ).get(pk=request_id)
        except (SpecificationGenerationRequest.DoesNotExist, ValueError, TypeError):
            return False
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        specification_id = (
            SpecificationGenerationRequest.objects.filter(pk=request_id)
            .values_list("specification_id", flat=True)
            .first()
        )
        specification = (
            Specification.objects.select_for_update()
            .filter(pk=specification_id)
            .first()
        )
        request = (
            SpecificationGenerationRequest.objects.select_for_update()
            .select_related("requested_by")
            .filter(pk=request_id)
            .first()
        )
        if (
            request is None
            or request.status != SpecificationGenerationStatus.RUNNING
            or request.execution_generation != generation
        ):
            return False
        if project is None or specification is None:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.FAILED,
                error_code="project_unavailable",
            )
            return False
        if (
            project.status not in WRITEABLE_PROJECT_STATUSES
            or specification.version != request.expected_version
            or get_project_member_role(
                project_id=project.pk,
                actor=request.requested_by,
            )
            != ProjectMemberRole.EXECUTOR
        ):
            _finish_request(
                request,
                status=SpecificationGenerationStatus.SUPERSEDED,
                error_code="draft_or_project_changed",
            )
            return False
        context = get_specification_generation_context(
            project=project,
            actor=request.requested_by,
        )
        if hash_source_context(context) != request.source_context_hash:
            _finish_request(
                request,
                status=SpecificationGenerationStatus.SUPERSEDED,
                error_code="sources_changed",
            )
            return False

        specification.content = content.strip()
        specification.status = SpecificationStatus.READY
        specification.updated_by = request.requested_by
        specification.version += 1
        specification.save(
            update_fields=("content", "status", "updated_by", "version", "updated_at")
        )
        _finish_request(request, status=SpecificationGenerationStatus.SUCCEEDED)
    return True


def fail_generation_request(*, request_id, generation, error):
    with transaction.atomic():
        request = (
            SpecificationGenerationRequest.objects.select_for_update()
            .filter(pk=request_id)
            .first()
        )
        if (
            request is None
            or request.status != SpecificationGenerationStatus.RUNNING
            or request.execution_generation != generation
        ):
            return False
        _finish_request(
            request,
            status=SpecificationGenerationStatus.FAILED,
            error_code=_safe_error_code(error),
        )
    return True
