import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.projects.models import Project


class QuestionnaireSubmissionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    CORRECTION_REQUESTED = "correction_requested", "Correction requested"


class QuestionnaireConflictStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RESOLVED = "resolved", "Resolved"


class QuestionnaireConflictDecision(models.TextChoices):
    KEEP_PASSPORT = "keep_passport", "Keep passport value"
    APPLY_ANSWER = "apply_answer", "Apply questionnaire answer"


class QuestionnaireAnswerOrigin(models.TextChoices):
    PREFILLED = "prefilled", "Prefilled from passport"
    CUSTOMER = "customer", "Provided by customer"


class QuestionnaireSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="questionnaire_submissions",
    )
    schema_key = models.CharField(max_length=64)
    schema_version = models.PositiveSmallIntegerField()
    passport_version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=32,
        choices=QuestionnaireSubmissionStatus.choices,
        default=QuestionnaireSubmissionStatus.DRAFT,
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="started_questionnaire_submissions",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="submitted_questionnaire_submissions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="superseding_submissions",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(schema_version__gte=1),
                name="questionnaire_schema_version_positive",
            ),
            models.CheckConstraint(
                condition=Q(status__in=QuestionnaireSubmissionStatus.values),
                name="questionnaire_submission_status_valid",
            ),
            models.UniqueConstraint(
                fields=("project",),
                condition=Q(status=QuestionnaireSubmissionStatus.DRAFT),
                name="one_questionnaire_draft_per_project",
            ),
        ]
        ordering = ("-started_at", "id")


class QuestionnaireAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        QuestionnaireSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question_key = models.CharField(max_length=100)
    value = models.JSONField()
    origin = models.CharField(
        max_length=16,
        choices=QuestionnaireAnswerOrigin.choices,
        default=QuestionnaireAnswerOrigin.CUSTOMER,
    )
    is_confirmed = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_questionnaire_answers",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("submission", "question_key"),
                name="unique_submission_question_answer",
            ),
            models.CheckConstraint(
                condition=Q(origin__in=QuestionnaireAnswerOrigin.values),
                name="questionnaire_answer_origin_valid",
            ),
        ]
        ordering = ("question_key", "id")


class QuestionnaireConflict(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        QuestionnaireSubmission,
        on_delete=models.CASCADE,
        related_name="conflicts",
    )
    answer = models.ForeignKey(
        QuestionnaireAnswer,
        on_delete=models.CASCADE,
        related_name="conflicts",
    )
    mapped_field = models.CharField(max_length=255)
    passport_value = models.JSONField()
    answer_value = models.JSONField()
    status = models.CharField(
        max_length=16,
        choices=QuestionnaireConflictStatus.choices,
        default=QuestionnaireConflictStatus.PENDING,
    )
    decision = models.CharField(
        max_length=24,
        choices=QuestionnaireConflictDecision.choices,
        blank=True,
        null=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="reviewed_questionnaire_conflicts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=QuestionnaireConflictStatus.values),
                name="questionnaire_conflict_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(decision__isnull=True)
                | Q(decision__in=QuestionnaireConflictDecision.values),
                name="questionnaire_conflict_decision_valid",
            ),
            models.UniqueConstraint(
                fields=("answer",),
                name="one_questionnaire_conflict_per_answer",
            ),
        ]
        indexes = [models.Index(fields=("submission", "status"))]
        ordering = ("created_at", "id")
