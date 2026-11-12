import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ProjectInvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REVOKED = "revoked", "Revoked"
    EXPIRED = "expired", "Expired"


class ProjectInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_invitations",
    )
    invited_email = models.EmailField(max_length=254)
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=16,
        choices=ProjectInvitationStatus.choices,
        default=ProjectInvitationStatus.PENDING,
    )
    expires_at = models.DateTimeField()
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="accepted_project_invitations",
        blank=True,
        null=True,
    )
    accepted_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ProjectInvitationStatus.values),
                name="project_invitation_status_valid",
            ),
            models.UniqueConstraint(
                fields=("project", "invited_email"),
                condition=Q(status=ProjectInvitationStatus.PENDING),
                name="one_pending_invite_project_email",
            ),
        ]
        indexes = [
            models.Index(
                fields=("project", "status", "expires_at"),
                name="inv_project_status_exp_idx",
            )
        ]

    def __str__(self):
        return f"ProjectInvitation({self.pk}, {self.status})"
