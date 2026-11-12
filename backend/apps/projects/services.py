from datetime import date
from decimal import Decimal

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


class ProjectInvitationUnavailableError(Exception):
    """The project lifecycle does not allow invitation acceptance."""

    def __init__(self, *, project_status):
        super().__init__(project_status)
        self.project_status = project_status


class ProjectCustomerAlreadyExistsError(Exception):
    """A different user already occupies the active customer role."""


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


def add_customer_member_from_invitation(*, project_id, user) -> ProjectMember:
    """Join the invited customer and activate a draft project atomically."""
    if user.email_verified_at is None:
        raise ProjectPermissionError

    with transaction.atomic():
        try:
            project = Project.objects.select_for_update().get(pk=project_id)
        except Project.DoesNotExist as exc:
            raise ProjectNotFoundError from exc

        if project.status not in {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}:
            raise ProjectInvitationUnavailableError(project_status=project.status)

        active_customer = (
            ProjectMember.objects.select_for_update()
            .filter(
                project=project,
                role=ProjectMemberRole.CUSTOMER,
                status=ProjectMemberStatus.ACTIVE,
            )
            .first()
        )
        if active_customer is not None and active_customer.user_id != user.pk:
            raise ProjectCustomerAlreadyExistsError

        membership = (
            ProjectMember.objects.select_for_update()
            .filter(project=project, user=user)
            .first()
        )
        if membership is None:
            membership = ProjectMember.objects.create(
                project=project,
                user=user,
                role=ProjectMemberRole.CUSTOMER,
                status=ProjectMemberStatus.ACTIVE,
            )
        elif membership.role != ProjectMemberRole.CUSTOMER:
            raise ProjectCustomerAlreadyExistsError
        elif membership.status != ProjectMemberStatus.ACTIVE:
            membership.status = ProjectMemberStatus.ACTIVE
            membership.save(update_fields=("status",))

        previous_status = project.status
        if previous_status == ProjectStatus.DRAFT:
            project.status = ProjectStatus.ACTIVE
            project.save(update_fields=("status", "updated_at"))
        if previous_status == ProjectStatus.DRAFT or active_customer is None:
            record_project_action(
                project_id=project.pk,
                actor_id=user.pk,
                action="project.customer_joined",
                target_type="project_member",
                target_id=membership.pk,
                metadata={
                    "from_status": previous_status,
                    "to_status": project.status,
                },
            )

    return membership


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


def lock_passport_for_update(*, project_id, actor, expected_version) -> ProjectPassport:
    """Lock and validate an executor's active-project passport for a transaction."""
    if (
        isinstance(expected_version, bool)
        or not isinstance(expected_version, int)
        or expected_version < 1
    ):
        raise ValidationError({"version": ["A positive version is required."]})

    with transaction.atomic():
        project = _get_executor_project_for_update(project_id=project_id, actor=actor)
        if project.status != ProjectStatus.ACTIVE:
            raise ProjectStateConflictError

        passport = (
            ProjectPassport.objects.select_for_update().filter(project=project).first()
        )
        if passport is None:
            raise ProjectNotFoundError
        if passport.version != expected_version:
            raise ProjectPassportVersionConflictError
        return passport


def apply_questionnaire_mapping(
    *, project_id, actor, expected_version, mapped_changes
) -> ProjectPassport:
    """Apply validated customer questionnaire mappings through the passport owner."""
    if not isinstance(mapped_changes, dict):
        raise ValidationError(
            {"non_field_errors": ["Mapped changes must be an object."]}
        )
    unknown_fields = set(mapped_changes) - PASSPORT_EDITABLE_FIELDS
    if unknown_fields:
        raise ValidationError(
            {"non_field_errors": ["Unknown questionnaire mappings were provided."]}
        )
    if (
        isinstance(expected_version, bool)
        or not isinstance(expected_version, int)
        or expected_version < 1
    ):
        raise ValidationError({"version": ["A positive version is required."]})

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
        if (
            membership.role != ProjectMemberRole.CUSTOMER
            or getattr(actor, "email_verified_at", None) is None
        ):
            raise ProjectPermissionError
        if project.status != ProjectStatus.ACTIVE:
            raise ProjectStateConflictError

        passport = (
            ProjectPassport.objects.select_for_update().filter(project=project).first()
        )
        if passport is None:
            raise ProjectNotFoundError
        if passport.version != expected_version:
            raise ProjectPassportVersionConflictError

        for field, value in mapped_changes.items():
            if field in {"goal", "target_audience", "expected_result"}:
                valid = isinstance(value, str)
            elif field == "deadline":
                valid = value is None or isinstance(value, date)
            elif field in {"budget_min", "budget_max"}:
                valid = value is None or isinstance(value, (str, int, Decimal))
            elif field == "currency":
                valid = value is None or isinstance(value, str)
            else:
                valid = isinstance(value, dict)
            if not valid:
                raise ValidationError(
                    {field: ["The mapped value has an invalid type."]}
                )

        changes = {
            field: value
            for field, value in mapped_changes.items()
            if getattr(passport, field) != value
        }
        if not changes:
            return passport

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
            action="project.questionnaire_mapped",
            target_type="passport",
            target_id=passport.pk,
            metadata={
                "changed_fields": sorted(changes),
                "previous_version": expected_version,
                "version": new_version,
            },
        )
    return passport
