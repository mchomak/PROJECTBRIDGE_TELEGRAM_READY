from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

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


class ProjectPassportVersionConflictError(Exception):
    """The passport version changed before the requested update could apply."""


PASSPORT_EDITABLE_FIELDS = {
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
}


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


def _get_executor_project_for_update(*, project_id, actor) -> Project:
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
    return project


def get_project_for_invitation_update(*, project_id, actor) -> Project:
    """Return the executor's locked project for an invitation mutation."""
    return _get_executor_project_for_update(project_id=project_id, actor=actor)


def _transition_project(
    *, project_id, actor, expected_statuses, target_status, action, extra_updates=None
) -> Project:
    with transaction.atomic():
        project = _get_executor_project_for_update(project_id=project_id, actor=actor)
        if project.status not in expected_statuses:
            raise ProjectStateConflictError

        previous_status = project.status
        updates = extra_updates(project, previous_status) if extra_updates else {}
        project.status = target_status
        for field, value in updates.items():
            setattr(project, field, value)
        update_fields = {"status", "updated_at", *updates}
        project.save(update_fields=sorted(update_fields))
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action=action,
            target_type="project",
            target_id=project.pk,
            metadata={"from_status": previous_status, "to_status": target_status},
        )
    return project


def complete_project(*, project_id, actor) -> Project:
    """Complete an active project without changing its memberships or data."""

    return _transition_project(
        project_id=project_id,
        actor=actor,
        expected_statuses={ProjectStatus.ACTIVE},
        target_status=ProjectStatus.COMPLETED,
        action="project.completed",
        extra_updates=lambda _project, _previous: {"completed_at": timezone.now()},
    )


def reopen_project(*, project_id, actor) -> Project:
    """Reopen a completed project; retain its most recent completion time."""

    return _transition_project(
        project_id=project_id,
        actor=actor,
        expected_statuses={ProjectStatus.COMPLETED},
        target_status=ProjectStatus.ACTIVE,
        action="project.reopened",
    )


def archive_project(*, project_id, actor) -> Project:
    """Archive an eligible project while preserving its former status."""

    return _transition_project(
        project_id=project_id,
        actor=actor,
        expected_statuses={
            ProjectStatus.DRAFT,
            ProjectStatus.ACTIVE,
            ProjectStatus.COMPLETED,
        },
        target_status=ProjectStatus.ARCHIVED,
        action="project.archived",
        extra_updates=lambda _project, previous: {
            "status_before_archive": previous,
            "archived_at": timezone.now(),
        },
    )


def restore_project(*, project_id, actor) -> Project:
    """Restore an archived project to its saved status and clear archive data."""

    with transaction.atomic():
        project = _get_executor_project_for_update(project_id=project_id, actor=actor)
        if (
            project.status != ProjectStatus.ARCHIVED
            or project.status_before_archive is None
        ):
            raise ProjectStateConflictError

        previous_status = project.status
        target_status = project.status_before_archive
        project.status = target_status
        project.status_before_archive = None
        project.archived_at = None
        project.save(
            update_fields=[
                "status",
                "status_before_archive",
                "archived_at",
                "updated_at",
            ]
        )
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project.restored",
            target_type="project",
            target_id=project.pk,
            metadata={"from_status": previous_status, "to_status": target_status},
        )
    return project


def update_passport(*, project_id, actor, expected_version, changes) -> ProjectPassport:
    """Apply an executor passport patch using an atomic version comparison."""

    if not isinstance(changes, dict) or not changes:
        raise ValidationError(
            {"non_field_errors": ["At least one passport field is required."]}
        )
    unknown_fields = set(changes) - PASSPORT_EDITABLE_FIELDS
    if unknown_fields:
        raise ValidationError(
            {"non_field_errors": ["Unknown passport fields were provided."]}
        )
    if (
        isinstance(expected_version, bool)
        or not isinstance(expected_version, int)
        or expected_version < 1
    ):
        raise ValidationError({"version": ["A positive version is required."]})

    with transaction.atomic():
        project = _get_executor_project_for_update(project_id=project_id, actor=actor)
        if project.status not in {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}:
            raise ProjectStateConflictError

        passport = ProjectPassport.objects.filter(project=project).first()
        if passport is None:
            raise ProjectNotFoundError

        new_version = expected_version + 1
        updated_count = ProjectPassport.objects.filter(
            pk=passport.pk,
            version=expected_version,
        ).update(
            **changes,
            version=F("version") + 1,
            updated_at=timezone.now(),
        )
        if updated_count != 1:
            raise ProjectPassportVersionConflictError

        passport.refresh_from_db()
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project.passport_updated",
            target_type="passport",
            target_id=passport.pk,
            metadata={
                "changed_fields": sorted(changes),
                "previous_version": expected_version,
                "version": new_version,
            },
        )
    return passport
