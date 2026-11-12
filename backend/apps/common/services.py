from uuid import UUID

from apps.projects.models import (
    ProjectMemberRole,
    ProjectStatus,
)

from .models import ProjectAuditLog

SAFE_METADATA_KEYS = {
    "changed_fields",
    "from_status",
    "to_status",
    "previous_version",
    "version",
    "role",
}
SAFE_STATUS_VALUES = {
    *ProjectStatus.values,
    "planned",
    "blocked",
    "cancelled",
    "draft",
    "confirmed",
    "in_progress",
    "rejected",
    "todo",
    "done",
    "open",
    "resolved",
    "dismissed",
    "unresolved",
}
SAFE_CHANGED_FIELDS = {
    "name",
    "description",
    "project_type",
    "status",
    "title",
    "goal",
    "target_audience",
    "expected_result",
    "functional_scope",
    "integrations",
    "constraints",
    "deadline",
    "budget_min",
    "budget_max",
    "currency",
    "additional_data",
    "position",
    "start_date",
    "due_date",
    "confirmed_by",
    "confirmed_at",
    "stage",
    "stage_id",
    "assignee_id",
    "question",
    "answer",
    "resolution",
    "evidence",
    "evidence_refs",
    "source_type",
    "source_id",
    "excerpt",
    "metadata",
}


def _validated_metadata(metadata):
    if not isinstance(metadata, dict) or set(metadata) - SAFE_METADATA_KEYS:
        raise ValueError("Project audit metadata contains unsupported fields.")

    safe_metadata = {}
    for key, value in metadata.items():
        if key == "changed_fields":
            if not isinstance(value, (list, tuple)) or any(
                not isinstance(field, str) or field not in SAFE_CHANGED_FIELDS
                for field in value
            ):
                raise ValueError("Project audit metadata contains unsupported fields.")
            safe_metadata[key] = list(value)
        elif key in {"from_status", "to_status"}:
            if value not in SAFE_STATUS_VALUES:
                raise ValueError("Project audit metadata contains an invalid status.")
            safe_metadata[key] = value
        elif key == "role":
            if value not in ProjectMemberRole.values:
                raise ValueError("Project audit metadata contains an invalid role.")
            safe_metadata[key] = value
        elif key in {"previous_version", "version"}:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Project audit metadata contains an invalid version.")
            safe_metadata[key] = value

    return safe_metadata


def record_project_action(
    *, project_id, actor_id, action, target_type, target_id, metadata
) -> ProjectAuditLog:
    safe_metadata = _validated_metadata(metadata)
    if isinstance(target_id, UUID):
        target_id = str(target_id)
    elif target_id is not None and (
        isinstance(target_id, bool) or not isinstance(target_id, (str, int))
    ):
        raise ValueError("Project audit target id must be a string, integer, or UUID.")

    return ProjectAuditLog.objects.create(
        project_id=project_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=None if target_id is None else str(target_id),
        metadata=safe_metadata,
    )
