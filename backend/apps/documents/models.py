import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class DocumentLifecycleStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVE_PENDING = "archive_pending", "Archive pending"
    ARCHIVED = "archived", "Archived"
    DELETION_PENDING = "deletion_pending", "Deletion pending"
    DELETED = "deleted", "Deleted"


class DocumentProcessingStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"
    UNSUPPORTED = "unsupported", "Unsupported"


class DocumentLifecycleAction(models.TextChoices):
    ARCHIVE = "archive", "Archive"
    PERMANENT_DELETE = "permanent_delete", "Permanent delete"


class DocumentLifecycleRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class DocumentLifecycleDecision(models.TextChoices):
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_project_documents",
    )
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=127)
    file_size = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    storage_key = models.CharField(max_length=512, unique=True)
    lifecycle_status = models.CharField(
        max_length=32,
        choices=DocumentLifecycleStatus.choices,
        default=DocumentLifecycleStatus.ACTIVE,
    )
    processing_status = models.CharField(
        max_length=16,
        choices=DocumentProcessingStatus.choices,
        default=DocumentProcessingStatus.QUEUED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(lifecycle_status__in=DocumentLifecycleStatus.values),
                name="document_lifecycle_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(processing_status__in=DocumentProcessingStatus.values),
                name="document_processing_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(checksum_sha256__regex=r"^[0-9a-f]{64}$"),
                name="document_sha256_valid",
            ),
        ]


class DocumentLifecycleRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="lifecycle_requests",
    )
    action = models.CharField(max_length=32, choices=DocumentLifecycleAction.choices)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_document_lifecycle_requests",
    )
    status = models.CharField(
        max_length=16,
        choices=DocumentLifecycleRequestStatus.choices,
        default=DocumentLifecycleRequestStatus.PENDING,
    )
    deletion_after = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(action__in=DocumentLifecycleAction.values),
                name="document_lifecycle_action_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=DocumentLifecycleRequestStatus.values),
                name="document_lifecycle_request_status_valid",
            ),
        ]


class DocumentLifecycleApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        DocumentLifecycleRequest,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_lifecycle_approvals",
    )
    decision = models.CharField(
        max_length=16,
        choices=DocumentLifecycleDecision.choices,
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("decided_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("request", "user"),
                name="unique_document_lifecycle_approval",
            ),
            models.CheckConstraint(
                condition=Q(decision__in=DocumentLifecycleDecision.values),
                name="document_lifecycle_decision_valid",
            ),
        ]
