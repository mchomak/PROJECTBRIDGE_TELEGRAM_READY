import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common.services import record_project_action
from apps.projects.models import (
    ProjectMemberRole,
    ProjectStatus,
)
from apps.projects.selectors import (
    get_project_invitation_context,
    has_active_customer_membership,
)
from apps.projects.services import (
    ProjectNotFoundError,
    ProjectPermissionError,
    get_project_for_invitation_update,
)

from .models import ProjectInvitation, ProjectInvitationStatus

INVITATION_EXPIRY = timedelta(days=7)
INVITATION_CREATE_LIMIT = 20
INVITATION_CREATE_WINDOW_SECONDS = 60 * 60


class InvitationNotFoundError(Exception):
    """The project or invitation is not visible to the actor."""


class InvitationPermissionError(Exception):
    """The actor cannot manage invitations for the project."""


class InvitationStateConflictError(Exception):
    """The project or invitation state does not allow this operation."""


class InvitationRateLimitError(Exception):
    """The executor exceeded the invitation creation limit."""


def _get_executor_project_for_read(*, project_id, actor):
    context = get_project_invitation_context(project_id=project_id, user=actor)
    if context is None:
        raise InvitationNotFoundError
    project, role = context
    if role != ProjectMemberRole.EXECUTOR:
        raise InvitationPermissionError
    return project


def _normalize_invited_email(invited_email):
    normalized_email = User.objects.normalize_email(invited_email)
    try:
        validate_email(normalized_email)
    except ValidationError as exc:
        raise ValidationError(
            {"invited_email": ["Enter a valid email address."]}
        ) from exc
    return normalized_email


def _enforce_create_limit(*, actor_id, now):
    hour_bucket = int(now.timestamp()) // INVITATION_CREATE_WINDOW_SECONDS
    cache_key = f"projectbridge:invitation:create:{actor_id}:{hour_bucket}"
    remaining_seconds = INVITATION_CREATE_WINDOW_SECONDS - (
        int(now.timestamp()) % INVITATION_CREATE_WINDOW_SECONDS
    )

    if cache.add(cache_key, 1, timeout=remaining_seconds):
        return

    try:
        count = cache.incr(cache_key)
    except ValueError:
        if cache.add(cache_key, 1, timeout=remaining_seconds):
            return
        count = cache.incr(cache_key)

    if count > INVITATION_CREATE_LIMIT:
        raise InvitationRateLimitError


def _send_invitation_email(*, invitation, project, raw_token):
    frontend_url = settings.FRONTEND_BASE_URL.rstrip("/")
    invitation_url = f"{frontend_url}/invite/#token={raw_token}"
    expiry = invitation.expires_at.isoformat()
    message = (
        f"You have been invited to join {project.name} on ProjectBridge.\n\n"
        f"Accept the invitation: {invitation_url}\n\n"
        f"This invitation expires at {expiry}."
    )
    sent_count = send_mail(
        subject=f"Invitation to {project.name}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.invited_email],
        fail_silently=False,
    )
    if sent_count != 1:
        raise RuntimeError("The invitation email was not delivered.")


def create_invitation(*, project_id, actor, invited_email):
    normalized_email = _normalize_invited_email(invited_email)
    now = timezone.now()

    with transaction.atomic():
        try:
            project = get_project_for_invitation_update(
                project_id=project_id,
                actor=actor,
            )
        except ProjectNotFoundError as exc:
            raise InvitationNotFoundError from exc
        except ProjectPermissionError as exc:
            raise InvitationPermissionError from exc

        if project.status not in {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}:
            raise InvitationStateConflictError
        if has_active_customer_membership(project_id=project.pk):
            raise InvitationStateConflictError

        ProjectInvitation.objects.filter(
            project=project,
            invited_email=normalized_email,
            status=ProjectInvitationStatus.PENDING,
            expires_at__lte=now,
        ).update(status=ProjectInvitationStatus.EXPIRED, updated_at=now)
        if ProjectInvitation.objects.filter(
            project=project,
            invited_email=normalized_email,
            status=ProjectInvitationStatus.PENDING,
            expires_at__gt=now,
        ).exists():
            raise InvitationStateConflictError

        _enforce_create_limit(actor_id=actor.pk, now=now)

        raw_token = secrets.token_urlsafe(32)
        invitation = ProjectInvitation.objects.create(
            project=project,
            created_by=actor,
            invited_email=normalized_email,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=now + INVITATION_EXPIRY,
        )
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="project.invitation_created",
            target_type="project_invitation",
            target_id=invitation.pk,
            metadata={},
        )
        _send_invitation_email(
            invitation=invitation,
            project=project,
            raw_token=raw_token,
        )

    return invitation


def get_project_invitations(*, project_id, actor):
    project = _get_executor_project_for_read(project_id=project_id, actor=actor)
    now = timezone.now()
    ProjectInvitation.objects.filter(
        project=project,
        status=ProjectInvitationStatus.PENDING,
        expires_at__lte=now,
    ).update(status=ProjectInvitationStatus.EXPIRED, updated_at=now)
    return ProjectInvitation.objects.filter(project=project).order_by(
        "-created_at", "id"
    )


def revoke_invitation(*, project_id, actor, invitation_id):
    expired_invitation = False
    invitation = None
    now = timezone.now()

    with transaction.atomic():
        try:
            project = get_project_for_invitation_update(
                project_id=project_id,
                actor=actor,
            )
        except ProjectNotFoundError as exc:
            raise InvitationNotFoundError from exc
        except ProjectPermissionError as exc:
            raise InvitationPermissionError from exc

        if project.status not in {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}:
            raise InvitationStateConflictError

        invitation = (
            ProjectInvitation.objects.select_for_update()
            .filter(project=project, pk=invitation_id)
            .first()
        )
        if invitation is None:
            raise InvitationNotFoundError
        if invitation.status != ProjectInvitationStatus.PENDING:
            raise InvitationStateConflictError
        if invitation.expires_at <= now:
            invitation.status = ProjectInvitationStatus.EXPIRED
            invitation.save(update_fields=("status", "updated_at"))
            expired_invitation = True
        else:
            invitation.status = ProjectInvitationStatus.REVOKED
            invitation.revoked_at = now
            invitation.save(update_fields=("status", "revoked_at", "updated_at"))
            record_project_action(
                project_id=project.pk,
                actor_id=actor.pk,
                action="project.invitation_revoked",
                target_type="project_invitation",
                target_id=invitation.pk,
                metadata={},
            )

    if expired_invitation:
        raise InvitationStateConflictError
    return invitation
