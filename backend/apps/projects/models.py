import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ProjectType(models.TextChoices):
    WEBSITE = "website", "Website"
    TELEGRAM_BOT = "telegram_bot", "Telegram bot"
    AUTOMATION = "automation", "Automation"
    OTHER = "other", "Other"


class ProjectStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class ProjectPreviousStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"


class ProjectMemberRole(models.TextChoices):
    EXECUTOR = "executor", "Executor"
    CUSTOMER = "customer", "Customer"


class ProjectMemberStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    LEFT = "left", "Left"
    REVOKED = "revoked", "Revoked"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    project_type = models.CharField(max_length=32, choices=ProjectType.choices)
    status = models.CharField(
        max_length=16,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
    )
    status_before_archive = models.CharField(
        max_length=16,
        choices=ProjectPreviousStatus.choices,
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(project_type__in=ProjectType.values),
                name="project_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ProjectStatus.values),
                name="project_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(status_before_archive__isnull=True)
                | Q(status_before_archive__in=ProjectPreviousStatus.values),
                name="project_prev_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=ProjectStatus.ARCHIVED,
                        status_before_archive__isnull=False,
                        archived_at__isnull=False,
                    )
                    | (
                        ~Q(status=ProjectStatus.ARCHIVED)
                        & Q(
                            status_before_archive__isnull=True,
                            archived_at__isnull=True,
                        )
                    )
                ),
                name="project_archive_consistent",
            ),
        ]


class ProjectMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_memberships",
    )
    role = models.CharField(max_length=16, choices=ProjectMemberRole.choices)
    status = models.CharField(
        max_length=16,
        choices=ProjectMemberStatus.choices,
        default=ProjectMemberStatus.ACTIVE,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "user"),
                name="unique_project_user_membership",
            ),
            models.UniqueConstraint(
                fields=("project", "role"),
                condition=Q(status=ProjectMemberStatus.ACTIVE),
                name="one_active_project_role",
            ),
            models.CheckConstraint(
                condition=Q(role__in=ProjectMemberRole.values),
                name="project_member_role_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ProjectMemberStatus.values),
                name="project_member_status_valid",
            ),
        ]


class ProjectPassport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="passport",
    )
    goal = models.TextField(blank=True, default="")
    target_audience = models.TextField(blank=True, default="")
    expected_result = models.TextField(blank=True, default="")
    functional_scope = models.JSONField(default=dict)
    integrations = models.JSONField(default=dict)
    constraints = models.JSONField(default=dict)
    deadline = models.DateField(blank=True, null=True)
    budget_min = models.DecimalField(
        max_digits=30,
        decimal_places=10,
        blank=True,
        null=True,
    )
    budget_max = models.DecimalField(
        max_digits=30,
        decimal_places=10,
        blank=True,
        null=True,
    )
    currency = models.CharField(max_length=3, blank=True, null=True)
    additional_data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
