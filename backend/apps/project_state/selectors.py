from django.db.models import Count, Prefetch

from apps.projects.models import (
    Project,
    ProjectMember,
    ProjectMemberStatus,
)
from apps.questionnaire.selectors import get_submitted_answer_evidence_options

from .models import (
    Evidence,
    OpenQuestion,
    ProjectConflict,
    ProjectStage,
    Requirement,
    Task,
)


def get_project_state_for_member(*, project_id, actor):
    project = (
        Project.objects.filter(
            pk=project_id,
            memberships__user=actor,
            memberships__status=ProjectMemberStatus.ACTIVE,
        )
        .annotate(
            stages_count=Count("project_stages", distinct=True),
            requirements_count=Count("requirements", distinct=True),
            tasks_count=Count("project_tasks", distinct=True),
            open_questions_count=Count("open_questions", distinct=True),
            conflicts_count=Count("project_conflicts", distinct=True),
        )
        .first()
    )
    return project


def _project_collection(*, model, project_id, actor, related=()):
    queryset = model.objects.filter(
        project_id=project_id,
        project__memberships__user=actor,
        project__memberships__status=ProjectMemberStatus.ACTIVE,
    )
    if related:
        queryset = queryset.select_related(*related)
    return queryset.distinct()


def get_project_stages_for_member(*, project_id, actor):
    return _project_collection(
        model=ProjectStage,
        project_id=project_id,
        actor=actor,
        related=("created_by",),
    )


def get_project_requirements_for_member(*, project_id, actor):
    return _project_collection(
        model=Requirement,
        project_id=project_id,
        actor=actor,
        related=("created_by", "confirmed_by"),
    )


def get_project_tasks_for_member(*, project_id, actor):
    return _project_collection(
        model=Task,
        project_id=project_id,
        actor=actor,
        related=("created_by", "stage", "assignee"),
    )


def get_project_open_questions_for_member(*, project_id, actor):
    return _project_collection(
        model=OpenQuestion,
        project_id=project_id,
        actor=actor,
        related=("created_by",),
    )


def get_project_conflicts_for_member(*, project_id, actor):
    return _project_collection(
        model=ProjectConflict,
        project_id=project_id,
        actor=actor,
        related=("created_by", "resolved_by"),
    ).prefetch_related(
        Prefetch(
            "evidence",
            queryset=Evidence.objects.order_by("created_at", "id"),
        )
    )


def get_project_record_for_member(*, model, record_id, actor):
    return (
        model.objects.filter(
            pk=record_id,
            project__memberships__user=actor,
            project__memberships__status=ProjectMemberStatus.ACTIVE,
        )
        .distinct()
        .first()
    )


def get_project_member_role(*, project_id, actor):
    return (
        ProjectMember.objects.filter(
            project_id=project_id,
            user=actor,
            status=ProjectMemberStatus.ACTIVE,
        )
        .values_list("role", flat=True)
        .first()
    )


def get_questionnaire_evidence_options_for_project(*, project_id):
    """Read submitted answers through their owning questionnaire selector."""
    return get_submitted_answer_evidence_options(project_id=project_id)
