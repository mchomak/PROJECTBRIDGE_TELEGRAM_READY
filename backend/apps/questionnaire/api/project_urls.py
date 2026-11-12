from django.urls import path

from .views import (
    ProjectQuestionnaireConflictListView,
    ProjectQuestionnaireView,
    StartQuestionnaireSubmissionView,
)

app_name = "questionnaire_project"

urlpatterns = [
    path("", ProjectQuestionnaireView.as_view(), name="project-questionnaire"),
    path(
        "conflicts/",
        ProjectQuestionnaireConflictListView.as_view(),
        name="project-questionnaire-conflicts",
    ),
    path(
        "submissions/",
        StartQuestionnaireSubmissionView.as_view(),
        name="questionnaire-submission-start",
    ),
]
