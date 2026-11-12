from django.urls import path

from .views import (
    OpenQuestionCollectionView,
    OpenQuestionRecordView,
    ProjectConflictCollectionView,
    ProjectConflictRecordView,
    ProjectStageCollectionView,
    ProjectStageRecordView,
    ProjectStateAggregateView,
    ProjectStateEvidenceOptionsView,
    RequirementCollectionView,
    RequirementRecordView,
    TaskCollectionView,
    TaskRecordView,
)

app_name = "project_state"

urlpatterns = [
    path(
        "projects/<uuid:project_id>/state/",
        ProjectStateAggregateView.as_view(),
        name="project-state-aggregate",
    ),
    path(
        "projects/<uuid:project_id>/evidence-options/",
        ProjectStateEvidenceOptionsView.as_view(),
        name="project-evidence-options",
    ),
    path(
        "projects/<uuid:project_id>/stages/",
        ProjectStageCollectionView.as_view(),
        name="project-stages",
    ),
    path(
        "stages/<uuid:record_id>/",
        ProjectStageRecordView.as_view(),
        name="stage-detail",
    ),
    path(
        "projects/<uuid:project_id>/requirements/",
        RequirementCollectionView.as_view(),
        name="project-requirements",
    ),
    path(
        "requirements/<uuid:record_id>/",
        RequirementRecordView.as_view(),
        name="requirement-detail",
    ),
    path(
        "projects/<uuid:project_id>/tasks/",
        TaskCollectionView.as_view(),
        name="project-tasks",
    ),
    path("tasks/<uuid:record_id>/", TaskRecordView.as_view(), name="task-detail"),
    path(
        "projects/<uuid:project_id>/open-questions/",
        OpenQuestionCollectionView.as_view(),
        name="project-open-questions",
    ),
    path(
        "open-questions/<uuid:record_id>/",
        OpenQuestionRecordView.as_view(),
        name="open-question-detail",
    ),
    path(
        "projects/<uuid:project_id>/conflicts/",
        ProjectConflictCollectionView.as_view(),
        name="project-conflicts",
    ),
    path(
        "conflicts/<uuid:record_id>/",
        ProjectConflictRecordView.as_view(),
        name="conflict-detail",
    ),
]
