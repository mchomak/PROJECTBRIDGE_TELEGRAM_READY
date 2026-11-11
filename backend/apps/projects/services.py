from django.core.exceptions import ValidationError
from django.db import transaction

from apps.common.services import record_project_action

from .models import (
    Project,
    ProjectMember,
    ProjectMemberRole,
    ProjectMemberStatus,
    ProjectPassport,
)


def create_project(*, actor, data) -> Project:
    """Create a draft project and its initial executor-owned data."""
    if not isinstance(data, dict):
        raise ValidationError("Project data must be an object.")

    allowed_fields = {"name", "project_type", "description"}
    unexpected_fields = set(data) - allowed_fields
    if unexpected_fields:
        raise ValidationError(
            {"non_field_errors": ["Unknown project fields were provided."]}
        )

    with transaction.atomic():
        project = Project.objects.create(
            name=data.get("name"),
            project_type=data.get("project_type"),
            description=data.get("description"),
            created_by=actor,
        )
        ProjectMember.objects.create(
            project=project,
            user=actor,
            role=ProjectMemberRole.EXECUTOR,
            status=ProjectMemberStatus.ACTIVE,
        )
        ProjectPassport.objects.create(project=project)
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project.created",
            target_type="project",
            target_id=project.pk,
            metadata={},
        )
    return project
