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
    QuestionnaireConfirmationRequiredError,
    QuestionnaireNotFoundError,
    QuestionnairePassportVersionConflictError,
    QuestionnairePermissionError,
    QuestionnaireStateConflictError,
    get_questionnaire_conflicts_for_project,
    get_questionnaire_for_project,
    refresh_submission_passport_version,
    request_correction,
    resolve_conflict,
    save_answers,
    start_submission,
    submit_submission,
)

from .serializers import (
    ProjectQuestionnaireResponseSerializer,
    QuestionnaireConflictResponseSerializer,
    QuestionnaireSubmissionResponseSerializer,
    RefreshQuestionnairePassportVersionSerializer,
    RequestQuestionnaireCorrectionSerializer,
    ResolveQuestionnaireConflictSerializer,
    SaveQuestionnaireAnswersSerializer,
    StartQuestionnaireSubmissionSerializer,
    SubmitQuestionnaireSubmissionSerializer,
)


class QuestionnaireConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The questionnaire draft cannot be changed in its current state."
    default_code = "conflict"


class QuestionnairePassportConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "The project passport changed after this questionnaire draft started."
    )
    default_code = "conflict"


def _translate_service_error(error):
    if isinstance(error, QuestionnaireNotFoundError):
        raise NotFound("The questionnaire is unavailable to your account.") from None
    if isinstance(error, QuestionnairePermissionError):
        raise PermissionDenied(
            "You do not have permission for this questionnaire action."
        ) from None
    if isinstance(error, QuestionnaireStateConflictError):
        raise QuestionnaireConflict from None
    if isinstance(error, QuestionnairePassportVersionConflictError):
        raise QuestionnairePassportConflict from None
    if isinstance(error, QuestionnaireConfirmationRequiredError):
        raise ValidationError(
            {"confirm_prefilled": ["Confirm the prefilled answers before submitting."]}
        ) from None
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
            "history": result["history"],
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
            and before["submission"].status == "draft"
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


class RefreshQuestionnairePassportVersionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_submission_refresh_passport_version",
        request=RefreshQuestionnairePassportVersionSerializer,
        responses={
            200: QuestionnaireSubmissionResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, submission_id):
        serializer = RefreshQuestionnairePassportVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = refresh_submission_passport_version(
                submission_id=submission_id,
                actor=request.user,
            )
        except (
            QuestionnaireNotFoundError,
            QuestionnairePermissionError,
            QuestionnaireStateConflictError,
        ) as exc:
            _translate_service_error(exc)
        return Response(QuestionnaireSubmissionResponseSerializer(submission).data)


class SubmitQuestionnaireSubmissionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_submission_submit",
        request=SubmitQuestionnaireSubmissionSerializer,
        responses={
            200: QuestionnaireSubmissionResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, submission_id):
        serializer = SubmitQuestionnaireSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submission = submit_submission(
                submission_id=submission_id,
                actor=request.user,
                confirm_prefilled=serializer.validated_data["confirm_prefilled"],
            )
        except (
            QuestionnaireNotFoundError,
            QuestionnairePermissionError,
            QuestionnaireStateConflictError,
            QuestionnairePassportVersionConflictError,
            QuestionnaireConfirmationRequiredError,
            QuestionnaireSchemaError,
        ) as exc:
            _translate_service_error(exc)
        return Response(QuestionnaireSubmissionResponseSerializer(submission).data)


class RequestQuestionnaireCorrectionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_submission_request_correction",
        request=RequestQuestionnaireCorrectionSerializer,
        responses={
            200: QuestionnaireSubmissionResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, submission_id):
        serializer = RequestQuestionnaireCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            correction = request_correction(
                submission_id=submission_id,
                actor=request.user,
            )
        except (
            QuestionnaireNotFoundError,
            QuestionnairePermissionError,
            QuestionnaireStateConflictError,
        ) as exc:
            _translate_service_error(exc)
        return Response(QuestionnaireSubmissionResponseSerializer(correction).data)


class ProjectQuestionnaireConflictListView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_project_conflicts_list",
        responses={
            200: QuestionnaireConflictResponseSerializer(many=True),
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        try:
            conflicts = get_questionnaire_conflicts_for_project(
                project_id=project_id,
                actor=request.user,
            )
        except (QuestionnaireNotFoundError, QuestionnairePermissionError) as exc:
            _translate_service_error(exc)
        return Response(
            QuestionnaireConflictResponseSerializer(conflicts, many=True).data
        )


class ResolveQuestionnaireConflictView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["questionnaire"],
        operation_id="questionnaire_conflict_resolve",
        request=ResolveQuestionnaireConflictSerializer,
        responses={
            200: QuestionnaireConflictResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, conflict_id):
        serializer = ResolveQuestionnaireConflictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conflict = resolve_conflict(
                conflict_id=conflict_id,
                actor=request.user,
                decision=serializer.validated_data["decision"],
                expected_passport_version=serializer.validated_data[
                    "expected_passport_version"
                ],
            )
        except (
            QuestionnaireNotFoundError,
            QuestionnairePermissionError,
            QuestionnaireStateConflictError,
            QuestionnairePassportVersionConflictError,
            QuestionnaireSchemaError,
        ) as exc:
            _translate_service_error(exc)
        return Response(QuestionnaireConflictResponseSerializer(conflict).data)
