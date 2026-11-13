import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class SpecificationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready"


class SpecificationGenerationStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    SUPERSEDED = "superseded", "Superseded"


class Specification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="specification",
    )
    content = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=SpecificationStatus.choices,
        default=SpecificationStatus.DRAFT,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_specifications",
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=SpecificationStatus.values),
                name="specification_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1),
                name="specification_version_positive",
            ),
        ]


class SpecificationGenerationRequest(models.Model):
    """Durable, idempotent state for one async draft-generation request."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="specification_generation_requests",
    )
    specification = models.ForeignKey(
        Specification,
        on_delete=models.CASCADE,
        related_name="generation_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_specification_generations",
    )
    idempotency_key = models.UUIDField()
    expected_version = models.PositiveIntegerField()
    source_context_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=SpecificationGenerationStatus.choices,
        default=SpecificationGenerationStatus.QUEUED,
    )
    dispatch_attempts = models.PositiveSmallIntegerField(default=0)
    dispatch_lease_expires_at = models.DateTimeField(blank=True, null=True)
    execution_generation = models.PositiveIntegerField(default=0)
    lease_expires_at = models.DateTimeField(blank=True, null=True)
    celery_task_id = models.UUIDField(default=uuid.uuid4, unique=True)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("project", "requested_by", "idempotency_key"),
                name="spec_generation_idempotency_unique",
            ),
            models.UniqueConstraint(
                fields=("project",),
                condition=Q(
                    status__in=(
                        SpecificationGenerationStatus.QUEUED,
                        SpecificationGenerationStatus.RUNNING,
                    )
                ),
                name="one_active_spec_generation_per_project",
            ),
            models.CheckConstraint(
                condition=Q(status__in=SpecificationGenerationStatus.values),
                name="spec_generation_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(expected_version__gte=1),
                name="spec_generation_expected_version_positive",
            ),
            models.CheckConstraint(
                condition=Q(source_context_hash__regex=r"^[0-9a-f]{64}$"),
                name="spec_generation_context_hash_valid",
            ),
        ]
