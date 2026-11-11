from django.core.exceptions import ValidationError
from django.db import transaction

from apps.common.services import record_project_action

from .models import (
    Project,
    ProjectMember,
    ProjectMemberRole,
    ProjectMemberStatus,
    ProjectPassport,
    ProjectStatus,
    ProjectType,
)


class ProjectNotFoundError(Exception):
    """An actor has no active membership in the requested project."""


class ProjectPermissionError(Exception):
    """The actor cannot perform the requested project operation."""


class ProjectStateConflictError(Exception):
    """The project state does not allow the requested metadata mutation."""


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


def update_project_metadata(*, project_id, actor, changes) -> Project:
    """Update executor-editable metadata and audit the changed field names."""
    if not isinstance(changes, dict) or not changes:
        raise ValidationError(
            {"non_field_errors": ["At least one metadata field is required."]}
        )

    allowed_fields = {"name", "project_type", "description"}
    unknown_fields = set(changes) - allowed_fields
    if unknown_fields:
        raise ValidationError(
            {"non_field_errors": ["Unknown project fields were provided."]}
        )
    if "name" in changes and (
        not isinstance(changes["name"], str) or not changes["name"].strip()
    ):
        raise ValidationError({"name": ["This field may not be blank."]})
    if "project_type" in changes and changes["project_type"] not in ProjectType.values:
        raise ValidationError({"project_type": ["Select a valid choice."]})
    if (
        "description" in changes
        and changes["description"] is not None
        and not isinstance(changes["description"], str)
    ):
        raise ValidationError({"description": ["Not a valid string."]})

    with transaction.atomic():
        try:
            project = Project.objects.select_for_update().get(pk=project_id)
        except Project.DoesNotExist as exc:
            raise ProjectNotFoundError from exc

        membership = ProjectMember.objects.filter(
            project=project,
            user=actor,
            status=ProjectMemberStatus.ACTIVE,
        ).first()
        if membership is None:
            raise ProjectNotFoundError
        if membership.role != ProjectMemberRole.EXECUTOR:
            raise ProjectPermissionError
        if project.status not in {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}:
            raise ProjectStateConflictError

        for field, value in changes.items():
            setattr(project, field, value)
        project.save(update_fields=[*changes, "updated_at"])
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project.metadata_updated",
            target_type="project",
            target_id=project.pk,
            metadata={"changed_fields": sorted(changes)},
        )
    return project
