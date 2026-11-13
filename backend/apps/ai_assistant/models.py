import hashlib
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q


class AITask(models.TextChoices):
    MESSAGE_ANALYSIS = "message_analysis", "Message analysis"
    CONVERSATION_ANALYSIS = "conversation_analysis", "Conversation analysis"
    CONTRADICTION_DETECTION = "contradiction_detection", "Contradiction detection"
    DOCUMENT_EMBEDDING = "document_embedding", "Document embedding"
    RAG_RERANKING = "rag_reranking", "RAG reranking"
    SPECIFICATION_GENERATION = "specification_generation", "Specification generation"


class AICapability(models.TextChoices):
    TEXT_GENERATION = "text_generation", "Text generation"
    EMBEDDINGS = "embeddings", "Embeddings"
    RERANKING = "reranking", "Reranking"


class AIAnalysisStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class AIAnalysisRequestStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class AIProposalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    APPLIED = "applied", "Applied"
    FAILED = "failed", "Failed"


class AIProposalType(models.TextChoices):
    REQUIREMENT_CREATE = "requirement_create", "Create requirement"
    OPEN_QUESTION_CREATE = "open_question_create", "Create open question"
    CONFLICT_CREATE = "conflict_create", "Create conflict"


class AIModelProfile(models.Model):
    """One immutable-versioned provider/model configuration for an AI task."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile_key = models.SlugField(max_length=64, unique=True)
    task_key = models.CharField(max_length=40, choices=AITask.choices)
    provider_key = models.CharField(max_length=32)
    model_name = models.CharField(max_length=128, blank=True)
    capabilities = models.JSONField(default=list)
    parameters = models.JSONField(default=dict)
    fallback_profile = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="fallback_for",
        blank=True,
        null=True,
    )
    is_default = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    config_version = models.PositiveIntegerField(default=1)
    embedding_space_version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("task_key", "profile_key")
        constraints = [
            models.UniqueConstraint(
                fields=("task_key",),
                condition=Q(is_default=True),
                name="unique_default_ai_profile_per_task",
            ),
            models.CheckConstraint(
                condition=Q(config_version__gte=1),
                name="ai_profile_config_version_positive",
            ),
            models.CheckConstraint(
                condition=Q(embedding_space_version__gte=1),
                name="ai_profile_embedding_space_version_positive",
            ),
        ]

    def clean(self):
        super().clean()
        if not isinstance(self.capabilities, list) or any(
            capability not in AICapability.values for capability in self.capabilities
        ):
            raise ValidationError({"capabilities": "Unsupported AI capability."})
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValidationError({"capabilities": "Capabilities must be unique."})
        required = {
            AITask.MESSAGE_ANALYSIS: AICapability.TEXT_GENERATION,
            AITask.CONVERSATION_ANALYSIS: AICapability.TEXT_GENERATION,
            AITask.CONTRADICTION_DETECTION: AICapability.TEXT_GENERATION,
            AITask.DOCUMENT_EMBEDDING: AICapability.EMBEDDINGS,
            AITask.RAG_RERANKING: AICapability.RERANKING,
            AITask.SPECIFICATION_GENERATION: AICapability.TEXT_GENERATION,
        }[self.task_key]
        if self.is_enabled and required not in self.capabilities:
            raise ValidationError(
                {"capabilities": f"Enabled task requires {required} capability."}
            )
        if self.is_enabled:
            from .providers import get_provider_capabilities

            provider = get_provider_capabilities(self.provider_key)
            if provider is None or required not in provider.capabilities:
                raise ValidationError(
                    {"provider_key": "Provider does not support this task capability."}
                )
        if not isinstance(self.parameters, dict):
            raise ValidationError({"parameters": "Parameters must be an object."})
        allowed_parameters = {
            "input_usd_per_million_tokens",
            "output_usd_per_million_tokens",
            "max_input_bytes",
            "max_output_tokens",
            "max_request_cost_usd",
            "daily_budget_usd",
            "timeout_seconds",
            "dimensions",
            "max_candidates",
            "reasoning_effort",
        }
        unknown_parameters = set(self.parameters) - allowed_parameters
        if unknown_parameters:
            raise ValidationError({"parameters": "Unsupported profile parameter."})
        if self.is_enabled:
            required_parameters = {
                "input_usd_per_million_tokens",
                "output_usd_per_million_tokens",
                "max_input_bytes",
                "max_output_tokens",
                "max_request_cost_usd",
                "daily_budget_usd",
                "timeout_seconds",
            }
            if required_parameters - set(self.parameters):
                raise ValidationError({"parameters": "Required AI limits are missing."})
            for parameter in (
                "input_usd_per_million_tokens",
                "output_usd_per_million_tokens",
                "max_request_cost_usd",
                "daily_budget_usd",
            ):
                try:
                    amount = Decimal(str(self.parameters[parameter]))
                except (InvalidOperation, ValueError, TypeError):
                    raise ValidationError(
                        {"parameters": "Cost parameters must be decimal values."}
                    ) from None
                if not amount.is_finite() or amount < 0:
                    raise ValidationError(
                        {"parameters": "Cost parameters must be non-negative."}
                    )
            integer_parameters = {
                "max_input_bytes": (1, 20 * 1024 * 1024),
                "max_output_tokens": (0, 8192),
                "timeout_seconds": (30, 60),
            }
            if self.task_key == AITask.RAG_RERANKING:
                integer_parameters["max_candidates"] = (1, 100)
                if "max_candidates" not in self.parameters:
                    raise ValidationError(
                        {"parameters": "Reranking requires a candidate limit."}
                    )
            for parameter, (minimum, maximum) in integer_parameters.items():
                if parameter not in self.parameters:
                    continue
                value = self.parameters[parameter]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or not minimum <= value <= maximum
                ):
                    raise ValidationError({"parameters": f"Invalid {parameter} limit."})
            if (
                self.task_key
                in (
                    AITask.MESSAGE_ANALYSIS,
                    AITask.CONVERSATION_ANALYSIS,
                    AITask.CONTRADICTION_DETECTION,
                    AITask.SPECIFICATION_GENERATION,
                    AITask.RAG_RERANKING,
                )
                and self.parameters["max_output_tokens"] < 1
            ):
                raise ValidationError(
                    {"parameters": "Text tasks require output tokens."}
                )
            if "dimensions" in self.parameters:
                dimensions = self.parameters["dimensions"]
                if isinstance(dimensions, bool) or not isinstance(dimensions, int):
                    raise ValidationError(
                        {"parameters": "Embedding dimensions must be an integer."}
                    )
                if dimensions != 1536:
                    raise ValidationError(
                        {"parameters": "Embedding profiles must use 1536 dimensions."}
                    )
            if (
                self.task_key == AITask.DOCUMENT_EMBEDDING
                and "dimensions" not in self.parameters
            ):
                raise ValidationError(
                    {"parameters": "Embedding profiles require dimensions."}
                )
            if self.parameters.get("reasoning_effort") not in (
                None,
                "low",
                "medium",
                "high",
            ):
                raise ValidationError({"parameters": "Invalid reasoning effort."})
        if self.fallback_profile_id:
            fallback = self.fallback_profile
            if fallback.task_key != self.task_key:
                raise ValidationError(
                    {"fallback_profile": "Fallback must serve the same task."}
                )
            if not fallback.is_enabled:
                raise ValidationError(
                    {"fallback_profile": "Fallback profile must be enabled."}
                )
            if not set(self.capabilities).issubset(set(fallback.capabilities)):
                raise ValidationError(
                    {"fallback_profile": "Fallback lacks a required capability."}
                )
            if fallback.fallback_profile_id:
                raise ValidationError(
                    {"fallback_profile": "Fallback chains may only have one level."}
                )
            if AICapability.EMBEDDINGS in self.capabilities and (
                fallback.provider_key != self.provider_key
                or fallback.model_name != self.model_name
                or fallback.parameters.get("dimensions")
                != self.parameters.get("dimensions")
                or fallback.embedding_space_key != self.embedding_space_key
                or fallback.embedding_space_version != self.embedding_space_version
            ):
                raise ValidationError(
                    {
                        "fallback_profile": (
                            "Embedding fallback must use the same vector space."
                        )
                    }
                )
        if self.is_enabled and not self.model_name:
            raise ValidationError(
                {"model_name": "An enabled profile requires a model."}
            )

    @property
    def embedding_space_key(self):
        """Stable identity for a provider/model/dimension vector space."""
        if self.task_key != AITask.DOCUMENT_EMBEDDING or not self.model_name:
            return ""
        dimensions = self.parameters.get("dimensions", 1536)
        signature = f"{self.provider_key}\0{self.model_name}\0{dimensions}"
        return f"embed-{hashlib.sha256(signature.encode()).hexdigest()[:58]}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            config_changed = False
            if self.pk and not self._state.adding:
                old = type(self).objects.select_for_update().filter(pk=self.pk).first()
                if old and any(
                    getattr(old, field) != getattr(self, field)
                    for field in (
                        "task_key",
                        "provider_key",
                        "model_name",
                        "capabilities",
                        "parameters",
                        "fallback_profile_id",
                        "is_default",
                        "is_enabled",
                    )
                ):
                    self.config_version = old.config_version + 1
                    config_changed = True
            self.full_clean()
            if config_changed and kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                    "config_version",
                    "updated_at",
                }
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task_key}: {self.profile_key} ({self.model_name or 'disabled'})"


class AIAnalysisRun(models.Model):
    """Content-free execution record for a provider call."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ai_analysis_runs",
    )
    profile = models.ForeignKey(
        AIModelProfile,
        on_delete=models.SET_NULL,
        related_name="analysis_runs",
        blank=True,
        null=True,
    )
    task_key = models.CharField(max_length=40, choices=AITask.choices)
    trigger_type = models.CharField(max_length=32, default="service")
    provider_key = models.CharField(max_length=32)
    model_name = models.CharField(max_length=128)
    profile_version = models.PositiveIntegerField()
    prompt_version = models.CharField(max_length=64, blank=True)
    input_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=AIAnalysisStatus.choices,
        default=AIAnalysisStatus.RUNNING,
    )
    input_tokens = models.PositiveIntegerField(blank=True, null=True)
    output_tokens = models.PositiveIntegerField(blank=True, null=True)
    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=8, blank=True, null=True
    )
    reserved_cost = models.DecimalField(
        max_digits=12, decimal_places=8, default=Decimal("0")
    )
    request_budget_limit = models.DecimalField(
        max_digits=12, decimal_places=8, default=Decimal("0")
    )
    daily_budget_limit = models.DecimalField(
        max_digits=12, decimal_places=8, default=Decimal("0")
    )
    error_code = models.CharField(max_length=64, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-started_at", "id")
        indexes = [models.Index(fields=("task_key", "started_at"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(profile_version__gte=1),
                name="ai_run_profile_version_positive",
            ),
            models.CheckConstraint(
                condition=Q(status__in=AIAnalysisStatus.values),
                name="ai_run_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(estimated_cost__isnull=True)
                | Q(estimated_cost__gte=Decimal("0")),
                name="ai_run_estimated_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_cost__gte=Decimal("0")),
                name="ai_run_reserved_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(request_budget_limit__gte=Decimal("0")),
                name="ai_run_request_budget_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(daily_budget_limit__gte=Decimal("0")),
                name="ai_run_daily_budget_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.task_key} {self.id} ({self.status})"


class AIAnalysisRequest(models.Model):
    """Durable executor-visible state for a queued manual analysis."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ai_analysis_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_ai_analyses",
    )
    run = models.ForeignKey(
        AIAnalysisRun,
        on_delete=models.SET_NULL,
        related_name="requests",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=16,
        choices=AIAnalysisRequestStatus.choices,
        default=AIAnalysisRequestStatus.QUEUED,
    )
    celery_task_id = models.UUIDField(default=uuid.uuid4, unique=True)
    dispatch_attempts = models.PositiveIntegerField(default=0)
    dispatch_failures = models.PositiveSmallIntegerField(default=0)
    dispatch_successful_at = models.DateTimeField(blank=True, null=True)
    dispatch_lease_expires_at = models.DateTimeField(blank=True, null=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4)
    execution_generation = models.PositiveIntegerField(default=0)
    lease_expires_at = models.DateTimeField(blank=True, null=True)
    result_count = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)
    context_prepared_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "id")
        indexes = [models.Index(fields=("project", "created_at"))]
        constraints = [
            models.UniqueConstraint(
                fields=("project", "requested_by", "idempotency_key"),
                name="unique_ai_analysis_idempotency_key",
            ),
            models.CheckConstraint(
                condition=Q(status__in=AIAnalysisRequestStatus.values),
                name="ai_request_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(result_count__lte=100),
                name="ai_request_result_count_bounded",
            ),
        ]


class AIProposal(models.Model):
    """Private, evidence-backed change suggestion awaiting executor action."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="ai_proposals"
    )
    analysis_run = models.ForeignKey(
        AIAnalysisRun, on_delete=models.CASCADE, related_name="proposals"
    )
    analysis_request = models.ForeignKey(
        AIAnalysisRequest, on_delete=models.CASCADE, related_name="proposals"
    )
    idempotency_key = models.CharField(max_length=64)
    proposal_type = models.CharField(max_length=32, choices=AIProposalType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    rationale = models.TextField(blank=True, default="")
    proposed_payload = models.JSONField(default=dict)
    final_payload = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=AIProposalStatus.choices,
        default=AIProposalStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_ai_proposals",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    applied_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("analysis_request", "idempotency_key"),
                name="unique_ai_proposal_per_request",
            ),
            models.CheckConstraint(
                condition=Q(proposal_type__in=AIProposalType.values),
                name="ai_proposal_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=AIProposalStatus.values),
                name="ai_proposal_status_valid",
            ),
        ]


class AIProposalEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(
        AIProposal, on_delete=models.CASCADE, related_name="evidence_links"
    )
    source_type = models.CharField(max_length=32)
    source_id = models.UUIDField()
    excerpt = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("proposal", "source_type", "source_id"),
                name="unique_ai_proposal_evidence",
            )
        ]


class AIAnalysisRequestEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        AIAnalysisRequest, on_delete=models.CASCADE, related_name="evidence_links"
    )
    source_type = models.CharField(max_length=32)
    source_id = models.UUIDField()
    excerpt = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("request", "source_type", "source_id"),
                name="unique_ai_analysis_request_evidence",
            )
        ]
