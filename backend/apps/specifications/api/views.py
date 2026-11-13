from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
)
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from apps.accounts.api.core.serializers import ErrorEnvelopeSerializer

from ..services import (
    SpecificationConflictError,
    SpecificationNotFoundError,
    SpecificationPermissionError,
    SpecificationVersionConflictError,
    get_latest_generation,
    get_specification,
    queue_specification_generation,
    update_specification,
)
from .serializers import (
    EmptyRequestSerializer,
    SpecificationGenerationRequestSerializer,
    SpecificationPatchSchemaSerializer,
    SpecificationPatchSerializer,
    SpecificationSerializer,
)


class SpecificationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        "The specification changed or cannot be modified in its current state."
    )
    default_code = "conflict"


class SpecificationVersionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The specification changed after it was loaded."
    default_code = "stale_specification_version"


def _translate_service_error(error):
    if isinstance(error, SpecificationNotFoundError):
        raise NotFound("The specification is unavailable to your account.") from None
    if isinstance(error, SpecificationPermissionError):
        raise PermissionDenied(
            "Only the project executor can generate or edit the specification."
        ) from None
    if isinstance(error, SpecificationVersionConflictError):
        raise SpecificationVersionConflict from None
    if isinstance(error, SpecificationConflictError):
        raise SpecificationConflict from None
    raise error


class ProjectSpecificationView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["specifications"],
        operation_id="project_specification_retrieve",
        responses={
            200: SpecificationSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        try:
            specification = get_specification(project_id=project_id, actor=request.user)
            generation = get_latest_generation(
                project_id=project_id, actor=request.user
            )
        except SpecificationNotFoundError as error:
            _translate_service_error(error)
        return Response(
            SpecificationSerializer(
                specification,
                context={"generation": generation},
            ).data
        )

    @extend_schema(
        tags=["specifications"],
        operation_id="project_specification_update",
        request=SpecificationPatchSchemaSerializer,
        responses={
            200: SpecificationSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def patch(self, request, project_id):
        serializer = SpecificationPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            specification = update_specification(
                project_id=project_id,
                actor=request.user,
                content=serializer.validated_data["content"],
                expected_version=serializer.validated_data["version"],
            )
            generation = get_latest_generation(
                project_id=project_id, actor=request.user
            )
        except (
            SpecificationConflictError,
            SpecificationNotFoundError,
            SpecificationPermissionError,
        ) as error:
            _translate_service_error(error)
        return Response(
            SpecificationSerializer(
                specification,
                context={"generation": generation},
            ).data
        )


class ProjectSpecificationGenerateView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["specifications"],
        operation_id="project_specification_generate",
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
        request=EmptyRequestSerializer,
        responses={
            202: SpecificationGenerationRequestSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, project_id):
        serializer = EmptyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = serializers.UUIDField().run_validation(
            request.headers.get("Idempotency-Key")
        )
        try:
            generation = queue_specification_generation(
                project_id=project_id,
                actor=request.user,
                idempotency_key=idempotency_key,
            )
        except (
            SpecificationConflictError,
            SpecificationNotFoundError,
            SpecificationPermissionError,
        ) as error:
            _translate_service_error(error)
        return Response(
            SpecificationGenerationRequestSerializer(generation).data,
            status=status.HTTP_202_ACCEPTED,
        )
