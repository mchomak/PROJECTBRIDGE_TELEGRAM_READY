import json
from datetime import date
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.chat.selectors import get_message_for_evidence
from apps.common.services import record_project_action
from apps.projects.models import (
    Project,
    ProjectMember,
    ProjectMemberRole,
    ProjectMemberStatus,
    ProjectStatus,
)
from apps.questionnaire.selectors import get_submitted_answer_for_evidence

from .models import (
    Evidence,
    EvidenceSourceType,
    OpenQuestion,
    OpenQuestionStatus,
    ProjectConflict,
    ProjectConflictStatus,
    ProjectStage,
    ProjectStageStatus,
    Requirement,
    RequirementStatus,
    Task,
    TaskStatus,
)


class ProjectStateNotFoundError(Exception):
    """The project or record is not available to the active member."""


class ProjectStatePermissionError(Exception):
    """The actor is not the executor for this project."""


class ProjectStateConflictError(Exception):
    """The project lifecycle or record transition disallows this write."""


WRITEABLE_PROJECT_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}
TERMINAL_STATUSES = {
    ProjectStageStatus.COMPLETED,
    ProjectStageStatus.CANCELLED,
    RequirementStatus.COMPLETED,
    RequirementStatus.REJECTED,
    TaskStatus.DONE,
    TaskStatus.CANCELLED,
    OpenQuestionStatus.RESOLVED,
    OpenQuestionStatus.DISMISSED,
    ProjectConflictStatus.RESOLVED,
    ProjectConflictStatus.DISMISSED,
}

TRANSITIONS = {
    ProjectStage: {
        "planned": {"active", "cancelled"},
        "active": {"blocked", "completed", "cancelled"},
        "blocked": {"active", "cancelled"},
    },
    Requirement: {
        "draft": {"confirmed", "rejected"},
        "confirmed": {"in_progress", "rejected"},
        "in_progress": {"blocked", "completed", "rejected"},
        "blocked": {"in_progress", "rejected"},
    },
    Task: {
        "todo": {"in_progress", "cancelled"},
        "in_progress": {"blocked", "done", "cancelled"},
        "blocked": {"in_progress", "cancelled"},
    },
    OpenQuestion: {"open": {"resolved", "dismissed"}},
    ProjectConflict: {"unresolved": {"resolved", "dismissed"}},
}


def _validation_error(field, detail):
    raise ValidationError({field: [detail]})


def _validate_object(data, *, allowed_fields, required_fields=()):
    if not isinstance(data, dict):
        raise ValidationError({"non_field_errors": ["Expected an object."]})
    unknown = set(data) - set(allowed_fields)
    if unknown:
        raise ValidationError(
            {"non_field_errors": ["Unknown Project State fields were provided."]}
        )
    missing = set(required_fields) - set(data)
    if missing:
        raise ValidationError(
            {field: ["This field is required."] for field in sorted(missing)}
        )
    if not data:
        raise ValidationError(
            {"non_field_errors": ["At least one Project State field is required."]}
        )
    return dict(data)


def _text(data, field, *, required=False, max_length=None):
    if field not in data:
        if required:
            _validation_error(field, "This field is required.")
        return
    value = data[field]
    if not isinstance(value, str):
        _validation_error(field, "Not a valid string.")
    value = value.strip()
    if required and not value:
        _validation_error(field, "This field may not be blank.")
    if max_length is not None and len(value) > max_length:
        _validation_error(
            field, f"Ensure this field has no more than {max_length} characters."
        )
    data[field] = value


def _date(data, field):
    if field not in data:
        return
    value = data[field]
    if value is None:
        return
    if isinstance(value, date):
        return
    if isinstance(value, str):
        try:
            data[field] = date.fromisoformat(value)
            return
        except ValueError:
            pass
    _validation_error(field, "Use a valid date in YYYY-MM-DD format.")


def _positive_position(data, field="position"):
    if field not in data:
        return
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _validation_error(field, "Ensure this value is a non-negative integer.")
    if value > 2_147_483_647:
        _validation_error(field, "Ensure this value is at most 2147483647.")


def _uuid_value(value, *, field):
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        _validation_error(field, "Enter a valid UUID.")


def _authorize_project_for_write(*, project_id, actor):
    try:
        project = Project.objects.select_for_update().get(pk=project_id)
    except (Project.DoesNotExist, ValueError, TypeError) as exc:
        raise ProjectStateNotFoundError from exc

    membership = ProjectMember.objects.filter(
        project_id=project.pk,
        user=actor,
        status=ProjectMemberStatus.ACTIVE,
    ).first()
    if membership is None:
        raise ProjectStateNotFoundError
    if membership.role != ProjectMemberRole.EXECUTOR:
        raise ProjectStatePermissionError
    if project.status not in WRITEABLE_PROJECT_STATUSES:
        raise ProjectStateConflictError
    return project


def _authorize_record_for_write(*, model, record_id, actor):
    try:
        project_id = (
            model.objects.filter(pk=record_id)
            .values_list("project_id", flat=True)
            .first()
        )
    except (ValueError, TypeError):
        project_id = None
    if project_id is None:
        raise ProjectStateNotFoundError
    project = _authorize_project_for_write(project_id=project_id, actor=actor)
    try:
        record = model.objects.select_for_update().get(
            pk=record_id, project_id=project.pk
        )
    except model.DoesNotExist as exc:
        raise ProjectStateNotFoundError from exc
    return project, record


def _create_state_record(*, model, project_id, actor, values, action, target_type):
    with transaction.atomic():
        project = _authorize_project_for_write(project_id=project_id, actor=actor)
        record = model.objects.create(project=project, created_by=actor, **values)
        changed_fields = sorted({*values.keys(), "status"})
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action=action,
            target_type=target_type,
            target_id=record.pk,
            metadata={"changed_fields": changed_fields},
        )
    return record


def _transition(*, record, model, changes, actor):
    if record.status in TERMINAL_STATUSES:
        raise ProjectStateConflictError
    if "status" not in changes:
        return None
    new_status = changes["status"]
    valid_statuses = {
        value for value, _label in model._meta.get_field("status").choices
    }
    if not isinstance(new_status, str) or new_status not in valid_statuses:
        _validation_error("status", "Select a valid choice.")
    if new_status not in TRANSITIONS[model].get(record.status, set()):
        raise ProjectStateConflictError

    previous_status = record.status
    record.status = new_status
    updates = {"status", "updated_at"}
    if model is Requirement and new_status == RequirementStatus.CONFIRMED:
        record.confirmed_by = actor
        record.confirmed_at = timezone.now()
        updates.update({"confirmed_by", "confirmed_at"})
    if model is OpenQuestion and new_status in {
        OpenQuestionStatus.RESOLVED,
        OpenQuestionStatus.DISMISSED,
    }:
        record.resolved_at = timezone.now()
        updates.add("resolved_at")
    if model is ProjectConflict and new_status in {
        ProjectConflictStatus.RESOLVED,
        ProjectConflictStatus.DISMISSED,
    }:
        record.resolved_by = actor
        record.resolved_at = timezone.now()
        updates.update({"resolved_by", "resolved_at"})
    return previous_status, updates


def _update_state_record(
    *,
    model,
    record_id,
    actor,
    changes,
    allowed_fields,
    normalize,
    action,
    target_type,
):
    values = _validate_object(changes, allowed_fields=allowed_fields)
    values = normalize(values)
    with transaction.atomic():
        project, record = _authorize_record_for_write(
            model=model,
            record_id=record_id,
            actor=actor,
        )
        if model is ProjectConflict and record.status in {
            ProjectConflictStatus.RESOLVED,
            ProjectConflictStatus.DISMISSED,
        }:
            raise ProjectStateConflictError
        previous_status = None
        update_fields = {"updated_at"}
        if "status" in values:
            previous_status, transition_fields = _transition(
                record=record,
                model=model,
                changes=values,
                actor=actor,
            )
            update_fields.update(transition_fields)

        for field, value in values.items():
            if field == "status":
                continue
            if field == "stage_id":
                record.stage_id = value
            elif field == "assignee_id":
                record.assignee_id = value
            else:
                setattr(record, field, value)
            update_fields.add(field)

        if (
            model is ProjectConflict
            and values.get("status") == ProjectConflictStatus.RESOLVED
        ):
            resolution = values.get("resolution", record.resolution)
            if not resolution.strip():
                _validation_error(
                    "resolution", "Enter the resolution before resolving."
                )

        record.save(update_fields=sorted(update_fields))
        metadata = {"changed_fields": sorted(values)}
        if previous_status is not None:
            metadata.update(
                {"from_status": previous_status, "to_status": record.status}
            )
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action=action,
            target_type=target_type,
            target_id=record.pk,
            metadata=metadata,
        )
    return record


def _normalize_stage(data):
    _text(data, "name", required="name" in data, max_length=200)
    _text(data, "description")
    _positive_position(data)
    _date(data, "start_date")
    _date(data, "due_date")
    return data


def create_project_stage(*, project_id, actor, data):
    values = _validate_object(
        data,
        allowed_fields={"name", "description", "position", "start_date", "due_date"},
        required_fields={"name"},
    )
    values = _normalize_stage(values)
    return _create_state_record(
        model=ProjectStage,
        project_id=project_id,
        actor=actor,
        values=values,
        action="project_state.stage_created",
        target_type="project_stage",
    )


def update_project_stage(*, record_id, actor, changes):
    return _update_state_record(
        model=ProjectStage,
        record_id=record_id,
        actor=actor,
        changes=changes,
        allowed_fields={
            "name",
            "description",
            "position",
            "start_date",
            "due_date",
            "status",
        },
        normalize=_normalize_stage,
        action="project_state.stage_updated",
        target_type="project_stage",
    )


def _normalize_requirement(data):
    _text(data, "title", required="title" in data, max_length=255)
    _text(data, "description")
    return data


def create_requirement(*, project_id, actor, data):
    values = _validate_object(
        data,
        allowed_fields={"title", "description"},
        required_fields={"title"},
    )
    values = _normalize_requirement(values)
    return _create_state_record(
        model=Requirement,
        project_id=project_id,
        actor=actor,
        values=values,
        action="project_state.requirement_created",
        target_type="requirement",
    )


def update_requirement(*, record_id, actor, changes):
    return _update_state_record(
        model=Requirement,
        record_id=record_id,
        actor=actor,
        changes=changes,
        allowed_fields={"title", "description", "status"},
        normalize=_normalize_requirement,
        action="project_state.requirement_updated",
        target_type="requirement",
    )


def _normalize_task(data, *, project=None):
    _text(data, "title", required="title" in data, max_length=255)
    _text(data, "description")
    _date(data, "due_date")
    for field in ("stage_id", "assignee_id"):
        if field in data:
            data[field] = _uuid_value(data[field], field=field)
    if project is not None and "stage_id" in data and data["stage_id"] is not None:
        if not ProjectStage.objects.filter(
            pk=data["stage_id"], project_id=project.pk
        ).exists():
            _validation_error("stage_id", "Select a stage in this project.")
    if (
        project is not None
        and "assignee_id" in data
        and data["assignee_id"] is not None
    ):
        if not ProjectMember.objects.filter(
            project_id=project.pk,
            user_id=data["assignee_id"],
            status=ProjectMemberStatus.ACTIVE,
        ).exists():
            _validation_error("assignee_id", "Select an active member of this project.")
    return data


def create_task(*, project_id, actor, data):
    values = _validate_object(
        data,
        allowed_fields={"title", "description", "stage_id", "assignee_id", "due_date"},
        required_fields={"title"},
    )
    values = _normalize_task(values)
    with transaction.atomic():
        project = _authorize_project_for_write(project_id=project_id, actor=actor)
        values = _normalize_task(values, project=project)
        if "stage_id" in values:
            values["stage_id"] = values.pop("stage_id")
        if "assignee_id" in values:
            values["assignee_id"] = values.pop("assignee_id")
        task = Task.objects.create(project=project, created_by=actor, **values)
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project_state.task_created",
            target_type="task",
            target_id=task.pk,
            metadata={"changed_fields": sorted({*values.keys(), "status"})},
        )
    return task


def update_task(*, record_id, actor, changes):
    values = _validate_object(
        changes,
        allowed_fields={
            "title",
            "description",
            "stage_id",
            "assignee_id",
            "due_date",
            "status",
        },
    )
    with transaction.atomic():
        project, task = _authorize_record_for_write(
            model=Task, record_id=record_id, actor=actor
        )
        values = _normalize_task(values, project=project)
        return _update_state_record(
            model=Task,
            record_id=record_id,
            actor=actor,
            changes=values,
            allowed_fields={
                "title",
                "description",
                "stage_id",
                "assignee_id",
                "due_date",
                "status",
            },
            normalize=lambda current: current,
            action="project_state.task_updated",
            target_type="task",
        )


def _normalize_question(data):
    _text(data, "question", required="question" in data)
    _text(data, "answer")
    return data


def create_open_question(*, project_id, actor, data):
    values = _validate_object(
        data,
        allowed_fields={"question", "answer"},
        required_fields={"question"},
    )
    values = _normalize_question(values)
    return _create_state_record(
        model=OpenQuestion,
        project_id=project_id,
        actor=actor,
        values=values,
        action="project_state.open_question_created",
        target_type="open_question",
    )


def update_open_question(*, record_id, actor, changes):
    return _update_state_record(
        model=OpenQuestion,
        record_id=record_id,
        actor=actor,
        changes=changes,
        allowed_fields={"question", "answer", "status"},
        normalize=_normalize_question,
        action="project_state.open_question_updated",
        target_type="open_question",
    )


def _snapshot_questionnaire_answer(*, project, source_id):
    answer = get_submitted_answer_for_evidence(
        project_id=project.pk, answer_id=source_id
    )
    if answer is None:
        raise ProjectStateNotFoundError
    return {
        "source_type": EvidenceSourceType.QUESTIONNAIRE_ANSWER,
        "source_id": answer.pk,
        "excerpt": json.dumps(answer.value, ensure_ascii=False, sort_keys=True),
        "metadata": {
            "question_key": answer.question_key,
            "schema_key": answer.submission.schema_key,
            "schema_version": answer.submission.schema_version,
            "submission_id": str(answer.submission_id),
        },
    }


def _snapshot_message(*, project, source_id):
    message = get_message_for_evidence(
        project_id=project.pk,
        message_id=source_id,
    )
    if message is None:
        raise ProjectStateNotFoundError
    return {
        "source_type": EvidenceSourceType.MESSAGE,
        "source_id": message.pk,
        "excerpt": message.content,
        "metadata": {
            "message_type": message.message_type,
            "sender_id": str(message.sender_id),
            "sent_at": message.created_at.isoformat(),
        },
    }


def _snapshot_evidence_source(*, project, source_type, source_id):
    if source_type == EvidenceSourceType.QUESTIONNAIRE_ANSWER:
        return _snapshot_questionnaire_answer(project=project, source_id=source_id)
    if source_type == EvidenceSourceType.MESSAGE:
        return _snapshot_message(project=project, source_id=source_id)
    _validation_error("evidence_refs", "This evidence source is not available.")


def _normalize_evidence_refs(refs):
    if not isinstance(refs, list) or len(refs) < 2:
        _validation_error(
            "evidence_refs", "At least two evidence references are required."
        )
    normalized = []
    seen = set()
    for index, reference in enumerate(refs):
        if not isinstance(reference, dict) or set(reference) != {
            "source_type",
            "source_id",
        }:
            _validation_error(
                f"evidence_refs.{index}", "Provide a source_type and source_id."
            )
        source_type = reference["source_type"]
        if source_type not in EvidenceSourceType.values:
            _validation_error(
                "evidence_refs", "This evidence source is not available yet."
            )
        source_id = _uuid_value(reference["source_id"], field="evidence_refs")
        source_key = (source_type, source_id)
        if source_key in seen:
            _validation_error("evidence_refs", "Evidence references must be unique.")
        seen.add(source_key)
        normalized.append(source_key)
    return normalized


def create_project_conflict(*, project_id, actor, data):
    values = _validate_object(
        data,
        allowed_fields={"title", "description", "evidence_refs"},
        required_fields={"title", "evidence_refs"},
    )
    _text(values, "title", required=True, max_length=255)
    _text(values, "description")
    source_ids = _normalize_evidence_refs(values.pop("evidence_refs"))

    with transaction.atomic():
        project = _authorize_project_for_write(project_id=project_id, actor=actor)
        snapshots = [
            _snapshot_evidence_source(
                project=project,
                source_type=source_type,
                source_id=source_id,
            )
            for source_type, source_id in source_ids
        ]
        conflict = ProjectConflict.objects.create(
            project=project,
            created_by=actor,
            **values,
        )
        evidence_rows = [
            Evidence.objects.create(project=project, **snapshot)
            for snapshot in snapshots
        ]
        conflict.evidence.add(*evidence_rows)
        for evidence in evidence_rows:
            record_project_action(
                project_id=project.pk,
                actor_id=actor.pk,
                action="project_state.evidence_created",
                target_type="evidence",
                target_id=evidence.pk,
                metadata={"changed_fields": ["source_id", "source_type"]},
            )
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project_state.conflict_created",
            target_type="project_conflict",
            target_id=conflict.pk,
            metadata={
                "changed_fields": ["description", "evidence_refs", "status", "title"]
            },
        )
    return conflict


def _normalize_conflict(data):
    _text(data, "title", required="title" in data, max_length=255)
    _text(data, "description")
    _text(data, "resolution")
    return data


def update_project_conflict(*, record_id, actor, changes):
    return _update_state_record(
        model=ProjectConflict,
        record_id=record_id,
        actor=actor,
        changes=changes,
        allowed_fields={"status", "resolution"},
        normalize=_normalize_conflict,
        action="project_state.conflict_updated",
        target_type="project_conflict",
    )
