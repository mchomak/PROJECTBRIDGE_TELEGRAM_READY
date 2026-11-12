from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from apps.accounts.api.core.serializers import ErrorEnvelopeSerializer
from apps.questionnaire.schemas.registry import QuestionnaireSchemaError
from apps.questionnaire.services import (
    QuestionnaireNotFoundError,
    QuestionnairePermissionError,
    QuestionnaireStateConflictError,
    get_questionnaire_for_project,
    save_answers,
    start_submission,
)

from .serializers import (
    ProjectQuestionnaireResponseSerializer,
    QuestionnaireSubmissionResponseSerializer,
    SaveQuestionnaireAnswersSerializer,
    StartQuestionnaireSubmissionSerializer,
)


class QuestionnaireConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The questionnaire draft cannot be changed in its current state."
    default_code = "conflict"


def _translate_service_error(error):
    if isinstance(error, QuestionnaireNotFoundError):
        raise NotFound("The questionnaire is unavailable to your account.") from None
    if isinstance(error, QuestionnairePermissionError):
        raise PermissionDenied(
            "Only the active customer can edit the questionnaire."
        ) from None
    if isinstance(error, QuestionnaireStateConflictError):
        raise QuestionnaireConflict from None
    if isinstance(error, QuestionnaireSchemaError):
        if error.field:
            message = str(error).removeprefix(f"{error.field}: ")
            raise ValidationError({error.field: [message]}) from None
        raise ValidationError({"non_field_errors": [str(error)]}) from None
    raise error


class ProjectQuestionnaireView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_project_read",
        responses={
            200: ProjectQuestionnaireResponseSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        try:
            result = get_questionnaire_for_project(
                project_id=project_id, actor=request.user
            )
        except (QuestionnaireNotFoundError, QuestionnairePermissionError) as exc:
            _translate_service_error(exc)
        payload = {
            "schema": result["schema"],
            "submission": result["submission"],
        }
        return Response(ProjectQuestionnaireResponseSerializer(payload).data)


class StartQuestionnaireSubmissionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_submission_start",
        request=StartQuestionnaireSubmissionSerializer,
        responses={
            200: QuestionnaireSubmissionResponseSerializer,
            201: QuestionnaireSubmissionResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, project_id):
        serializer = StartQuestionnaireSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            before = get_questionnaire_for_project(
                project_id=project_id, actor=request.user
            )
            submission = start_submission(project_id=project_id, actor=request.user)
        except (
            QuestionnaireNotFoundError,
            QuestionnairePermissionError,
            QuestionnaireStateConflictError,
            QuestionnaireSchemaError,
        ) as exc:
            _translate_service_error(exc)

        response_status = (
            status.HTTP_200_OK
            if before["submission"] is not None
            else status.HTTP_201_CREATED
        )
        return Response(
            QuestionnaireSubmissionResponseSerializer(submission).data,
            status=response_status,
        )


class SaveQuestionnaireAnswersView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_answers_save",
        request=SaveQuestionnaireAnswersSerializer,
        responses={
            200: QuestionnaireSubmissionResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def patch(self, request, submission_id):
        serializer = SaveQuestionnaireAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = save_answers(
                submission_id=submission_id,
                actor=request.user,
                answers=serializer.validated_data["answers"],
            )
        except (
            QuestionnaireNotFoundError,
            QuestionnairePermissionError,
            QuestionnaireStateConflictError,
            QuestionnaireSchemaError,
        ) as exc:
            _translate_service_error(exc)
        return Response(QuestionnaireSubmissionResponseSerializer(submission).data)
