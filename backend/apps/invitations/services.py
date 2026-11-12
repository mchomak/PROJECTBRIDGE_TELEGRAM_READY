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
    ProjectCustomerAlreadyExistsError,
    ProjectInvitationUnavailableError,
    ProjectNotFoundError,
    ProjectPermissionError,
    add_customer_member_from_invitation,
    get_project_for_invitation_update,
)

from .models import ProjectInvitation, ProjectInvitationStatus

INVITATION_EXPIRY = timedelta(days=7)
INVITATION_CREATE_LIMIT = 20
INVITATION_CREATE_WINDOW_SECONDS = 60 * 60
INVITATION_PREVIEW_LIMIT = 30
INVITATION_ACCEPT_LIMIT = 10


class InvitationNotFoundError(Exception):
    """The project or invitation is not visible to the actor."""


class InvitationPermissionError(Exception):
    """The actor cannot manage invitations for the project."""


class InvitationStateConflictError(Exception):
    """The project or invitation state does not allow this operation."""


class InvitationRateLimitError(Exception):
    """The invitation request exceeded its rate limit."""


class InvitationUnavailableError(Exception):
    """A known invitation cannot be used in its current state."""

    def __init__(self, *, code, detail, status_code=410):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InvitationEmailMismatchError(Exception):
    """The actor does not own the email address invited to the project."""


class InvitationEmailUnverifiedError(Exception):
    """The actor has not verified their account email address."""


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


def _enforce_rate_limit(*, scope, identity, limit, now):
    hour_bucket = int(now.timestamp()) // INVITATION_CREATE_WINDOW_SECONDS
    cache_key = f"projectbridge:invitation:{scope}:{identity}:{hour_bucket}"
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

    if count > limit:
        raise InvitationRateLimitError


def enforce_invitation_preview_limit(*, client_ip):
    _enforce_rate_limit(
        scope="preview",
        identity=client_ip or "unknown",
        limit=INVITATION_PREVIEW_LIMIT,
        now=timezone.now(),
    )


def _enforce_accept_limit(*, actor_id, now):
    _enforce_rate_limit(
        scope="accept",
        identity=actor_id,
        limit=INVITATION_ACCEPT_LIMIT,
        now=now,
    )


def _mask_invited_email(invited_email):
    local_part, domain = invited_email.rsplit("@", maxsplit=1)
    return f"{local_part[:1]}***@{domain}"


def preview_invitation(raw_token):
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = (
        ProjectInvitation.objects.select_related("project")
        .filter(token_hash=token_hash)
        .first()
    )
    if invitation is None:
        raise InvitationNotFoundError

    now = timezone.now()
    if (
        invitation.status == ProjectInvitationStatus.PENDING
        and invitation.expires_at <= now
    ):
        ProjectInvitation.objects.filter(
            pk=invitation.pk,
            status=ProjectInvitationStatus.PENDING,
        ).update(status=ProjectInvitationStatus.EXPIRED, updated_at=now)
        raise InvitationUnavailableError(
            code="invitation_expired",
            detail="This invitation has expired.",
        )
    if invitation.status == ProjectInvitationStatus.EXPIRED:
        raise InvitationUnavailableError(
            code="invitation_expired",
            detail="This invitation has expired.",
        )
    if invitation.status == ProjectInvitationStatus.REVOKED:
        raise InvitationUnavailableError(
            code="invitation_revoked",
            detail="This invitation has been revoked.",
        )
    if invitation.status == ProjectInvitationStatus.ACCEPTED:
        return {
            "project_name": invitation.project.name,
            "email_hint": _mask_invited_email(invitation.invited_email),
            "expires_at": invitation.expires_at,
            "status": invitation.status,
        }
    if invitation.project.status == ProjectStatus.COMPLETED:
        raise InvitationUnavailableError(
            code="project_completed",
            detail="This project no longer accepts invitations.",
            status_code=409,
        )
    if invitation.project.status == ProjectStatus.ARCHIVED:
        raise InvitationUnavailableError(
            code="project_archived",
            detail="This project no longer accepts invitations.",
            status_code=409,
        )

    return {
        "project_name": invitation.project.name,
        "email_hint": _mask_invited_email(invitation.invited_email),
        "expires_at": invitation.expires_at,
        "status": invitation.status,
    }


def _raise_invitation_unavailable_for_project_status(project_status):
    if project_status == ProjectStatus.COMPLETED:
        raise InvitationUnavailableError(
            code="project_completed",
            detail="This project no longer accepts invitations.",
            status_code=409,
        )
    if project_status == ProjectStatus.ARCHIVED:
        raise InvitationUnavailableError(
            code="project_archived",
            detail="This project no longer accepts invitations.",
            status_code=409,
        )


def accept_invitation(*, actor, raw_token):
    now = timezone.now()
    _enforce_accept_limit(actor_id=str(actor.pk), now=now)

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = (
        ProjectInvitation.objects.select_related("project")
        .filter(token_hash=token_hash)
        .first()
    )
    if invitation is None:
        raise InvitationNotFoundError
    if actor.email_verified_at is None:
        raise InvitationEmailUnverifiedError
    if User.objects.normalize_email(actor.email) != invitation.invited_email:
        raise InvitationEmailMismatchError
    if invitation.status == ProjectInvitationStatus.EXPIRED:
        raise InvitationUnavailableError(
            code="invitation_expired",
            detail="This invitation has expired.",
        )
    if invitation.status == ProjectInvitationStatus.REVOKED:
        raise InvitationUnavailableError(
            code="invitation_revoked",
            detail="This invitation has been revoked.",
        )
    if invitation.status == ProjectInvitationStatus.ACCEPTED:
        if invitation.accepted_by_id == actor.pk:
            return invitation
        raise InvitationStateConflictError
    if invitation.expires_at <= now:
        ProjectInvitation.objects.filter(
            pk=invitation.pk,
            status=ProjectInvitationStatus.PENDING,
        ).update(status=ProjectInvitationStatus.EXPIRED, updated_at=now)
        raise InvitationUnavailableError(
            code="invitation_expired",
            detail="This invitation has expired.",
        )

    try:
        with transaction.atomic():
            add_customer_member_from_invitation(
                project_id=invitation.project_id,
                user=actor,
            )
            accepted_at = timezone.now()
            updated_count = ProjectInvitation.objects.filter(
                pk=invitation.pk,
                status=ProjectInvitationStatus.PENDING,
                expires_at__gt=accepted_at,
            ).update(
                status=ProjectInvitationStatus.ACCEPTED,
                accepted_by=actor,
                accepted_at=accepted_at,
                updated_at=accepted_at,
            )
            if updated_count != 1:
                invitation.refresh_from_db()
                if (
                    invitation.status == ProjectInvitationStatus.ACCEPTED
                    and invitation.accepted_by_id == actor.pk
                ):
                    return invitation
                if (
                    invitation.status == ProjectInvitationStatus.PENDING
                    and invitation.expires_at <= accepted_at
                ):
                    raise InvitationUnavailableError(
                        code="invitation_expired",
                        detail="This invitation has expired.",
                    )
                if invitation.status == ProjectInvitationStatus.EXPIRED:
                    raise InvitationUnavailableError(
                        code="invitation_expired",
                        detail="This invitation has expired.",
                    )
                if invitation.status == ProjectInvitationStatus.REVOKED:
                    raise InvitationUnavailableError(
                        code="invitation_revoked",
                        detail="This invitation has been revoked.",
                    )
                raise InvitationStateConflictError

            invitation.status = ProjectInvitationStatus.ACCEPTED
            invitation.accepted_by = actor
            invitation.accepted_at = accepted_at
            record_project_action(
                project_id=invitation.project_id,
                actor_id=actor.pk,
                action="project.invitation_accepted",
                target_type="project_invitation",
                target_id=invitation.pk,
                metadata={},
            )
    except ProjectCustomerAlreadyExistsError as exc:
        raise InvitationStateConflictError from exc
    except ProjectInvitationUnavailableError as exc:
        _raise_invitation_unavailable_for_project_status(exc.project_status)
        raise InvitationStateConflictError from exc
    except ProjectNotFoundError as exc:
        raise InvitationNotFoundError from exc
    except ProjectPermissionError as exc:
        raise InvitationEmailUnverifiedError from exc

    return invitation


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
