import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ProjectStageStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    BLOCKED = "blocked", "Blocked"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class RequirementStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"
    IN_PROGRESS = "in_progress", "In progress"
    BLOCKED = "blocked", "Blocked"
    COMPLETED = "completed", "Completed"
    REJECTED = "rejected", "Rejected"


class TaskStatus(models.TextChoices):
    TODO = "todo", "To do"
    IN_PROGRESS = "in_progress", "In progress"
    BLOCKED = "blocked", "Blocked"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


class OpenQuestionStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class ProjectConflictStatus(models.TextChoices):
    UNRESOLVED = "unresolved", "Unresolved"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class EvidenceSourceType(models.TextChoices):
    QUESTIONNAIRE_ANSWER = "questionnaire_answer", "Questionnaire answer"
    MESSAGE = "message", "Message"
    DOCUMENT_CHUNK = "document_chunk", "Document chunk"
    PASSPORT = "passport", "Project passport"


class ProjectStage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_stages",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    position = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=ProjectStageStatus.choices,
        default=ProjectStageStatus.PLANNED,
    )
    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_stages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")
        indexes = [models.Index(fields=("project", "status"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ProjectStageStatus.values),
                name="project_stage_status_valid",
            ),
        ]


class Requirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=RequirementStatus.choices,
        default=RequirementStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_requirements",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="confirmed_project_requirements",
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [models.Index(fields=("project", "status"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=RequirementStatus.values),
                name="requirement_status_valid",
            ),
        ]


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_tasks",
    )
    stage = models.ForeignKey(
        ProjectStage,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_project_tasks",
    )
    due_date = models.DateField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date", "created_at", "id")
        indexes = [models.Index(fields=("project", "status"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=TaskStatus.values),
                name="project_task_status_valid",
            ),
        ]


class OpenQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="open_questions",
    )
    question = models.TextField()
    answer = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=OpenQuestionStatus.choices,
        default=OpenQuestionStatus.OPEN,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_questions",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [models.Index(fields=("project", "status"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=OpenQuestionStatus.values),
                name="open_question_status_valid",
            ),
        ]


class ImmutableSnapshotQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Evidence snapshots are immutable.")

    def delete(self):
        raise ValidationError("Evidence snapshots are immutable.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Evidence snapshots are immutable.")

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        if update_conflicts:
            raise ValidationError("Evidence snapshots are immutable.")
        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


class Evidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_state_evidence",
    )
    source_type = models.CharField(max_length=32, choices=EvidenceSourceType.choices)
    source_id = models.UUIDField()
    excerpt = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager.from_queryset(ImmutableSnapshotQuerySet)()

    class Meta:
        ordering = ("created_at", "id")
        indexes = [models.Index(fields=("project", "source_type", "source_id"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(source_type__in=EvidenceSourceType.values),
                name="evidence_source_type_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Evidence snapshots are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Evidence snapshots are immutable.")


class ProjectConflictEvidenceQuerySet(ImmutableSnapshotQuerySet):
    def update(self, **kwargs):
        raise ValidationError("Conflict evidence links are immutable.")

    def delete(self):
        raise ValidationError("Conflict evidence links are immutable.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Conflict evidence links are immutable.")

    def bulk_create(self, objs, *args, **kwargs):
        links = list(objs)
        if not links:
            return super().bulk_create(links, *args, **kwargs)

        conflict_ids = {link.conflict_id for link in links}
        if self.filter(conflict_id__in=conflict_ids).exists():
            raise ValidationError("Conflict evidence links are immutable.")

        conflicts = {
            pk: (project_id, status)
            for pk, project_id, status in ProjectConflict.objects.filter(
                pk__in=conflict_ids
            ).values_list("pk", "project_id", "status")
        }
        evidence_ids = {link.evidence_id for link in links}
        evidence_projects = dict(
            Evidence.objects.filter(pk__in=evidence_ids).values_list("pk", "project_id")
        )
        if any(
            conflicts.get(link.conflict_id) is None
            or evidence_projects.get(link.evidence_id) is None
            or conflicts[link.conflict_id][0] != evidence_projects[link.evidence_id]
            or conflicts[link.conflict_id][1] != ProjectConflictStatus.UNRESOLVED
            for link in links
        ):
            raise ValidationError("Conflict evidence must belong to the same project.")
        return super().bulk_create(links, *args, **kwargs)


class ProjectConflict(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="project_conflicts",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=ProjectConflictStatus.choices,
        default=ProjectConflictStatus.UNRESOLVED,
    )
    resolution = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="resolved_project_conflicts",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    evidence = models.ManyToManyField(
        Evidence,
        through="ProjectConflictEvidence",
        related_name="conflicts",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_project_conflicts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [models.Index(fields=("project", "status"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=ProjectConflictStatus.values),
                name="project_conflict_status_valid",
            ),
        ]


class ProjectConflictEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conflict = models.ForeignKey(
        ProjectConflict,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )
    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.PROTECT,
        related_name="conflict_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager.from_queryset(ProjectConflictEvidenceQuerySet)()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("conflict", "evidence"),
                name="project_conflict_evidence_unique",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Conflict evidence links are immutable.")
        if self.conflict_id and self.evidence_id:
            if self.conflict.evidence_links.exists():
                raise ValidationError("Conflict evidence links are immutable.")
            if self.conflict.status != ProjectConflictStatus.UNRESOLVED:
                raise ValidationError("Conflict evidence links are immutable.")
            if self.conflict.project_id != self.evidence.project_id:
                raise ValidationError(
                    "Conflict evidence must belong to the same project."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Conflict evidence links are immutable.")
