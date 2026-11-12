from django.urls import path

from .views import SaveQuestionnaireAnswersView

app_name = "questionnaire"

urlpatterns = [
    path(
        "submissions/<uuid:submission_id>/answers/",
        SaveQuestionnaireAnswersView.as_view(),
        name="questionnaire-answers",
    ),
]
