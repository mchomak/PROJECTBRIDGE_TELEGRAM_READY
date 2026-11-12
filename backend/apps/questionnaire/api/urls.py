from django.urls import path

from .views import (
    RefreshQuestionnairePassportVersionView,
    RequestQuestionnaireCorrectionView,
    ResolveQuestionnaireConflictView,
    SaveQuestionnaireAnswersView,
    SubmitQuestionnaireSubmissionView,
)

app_name = "questionnaire"

urlpatterns = [
    path(
        "submissions/<uuid:submission_id>/refresh-passport-version/",
        RefreshQuestionnairePassportVersionView.as_view(),
        name="questionnaire-submission-refresh-passport-version",
    ),
    path(
        "submissions/<uuid:submission_id>/submit/",
        SubmitQuestionnaireSubmissionView.as_view(),
        name="questionnaire-submission-submit",
    ),
    path(
        "submissions/<uuid:submission_id>/request-correction/",
        RequestQuestionnaireCorrectionView.as_view(),
        name="questionnaire-submission-request-correction",
    ),
    path(
        "submissions/<uuid:submission_id>/answers/",
        SaveQuestionnaireAnswersView.as_view(),
        name="questionnaire-answers",
    ),
    path(
        "conflicts/<uuid:conflict_id>/resolve/",
        ResolveQuestionnaireConflictView.as_view(),
        name="questionnaire-conflict-resolve",
    ),
]
