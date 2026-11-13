from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)

from ..services import (
    AIWorkspaceConflictError,
    AIWorkspaceNotFoundError,
    AIWorkspacePermissionError,
    apply_ai_proposal,
    get_ai_proposal,
    get_analysis_request,
    list_ai_proposals,
    list_analysis_requests,
    queue_manual_analysis,
    reject_ai_proposal,
)
from .serializers import (
    AIAnalysisRequestPageSerializer,
    AIAnalysisRequestSerializer,
    AIProposalPageSerializer,
    AIProposalSerializer,
    ApplyEditedProposalSerializer,
    EmptyRequestSerializer,
)


class AIWorkspaceConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The AI workspace action conflicts with the current state."
    default_code = "conflict"


def _translate_service_error(error):
    if isinstance(error, AIWorkspaceNotFoundError):
        raise NotFound(
            "The AI workspace record is unavailable to your account."
        ) from None
    if isinstance(error, AIWorkspacePermissionError):
        raise PermissionDenied(
            "Only the project executor can access the AI workspace."
        ) from None
    if isinstance(error, AIWorkspaceConflictError):
        raise AIWorkspaceConflict from None
    if isinstance(error, DjangoValidationError):
        detail = (
            error.message_dict
            if hasattr(error, "message_dict")
            else {"non_field_errors": error.messages}
        )
        raise ValidationError(detail) from None
    raise error


class AIWorkspacePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AIAnalysisCollectionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_analysis_list",
        responses={200: AIAnalysisRequestPageSerializer},
    )
    def get(self, request, project_id):
        try:
            records = list_analysis_requests(project_id=project_id, actor=request.user)
        except (AIWorkspaceNotFoundError, AIWorkspacePermissionError) as error:
            _translate_service_error(error)
        paginator = AIWorkspacePagination()
        page = paginator.paginate_queryset(records, request, view=self)
        return paginator.get_paginated_response(
            AIAnalysisRequestSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_analysis_create",
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.HEADER,
                required=True,
            )
        ],
        request=EmptyRequestSerializer,
        responses={202: AIAnalysisRequestSerializer},
    )
    def post(self, request, project_id):
        serializer = EmptyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key_field = serializers.UUIDField(required=True)
        idempotency_key = key_field.run_validation(
            request.headers.get("Idempotency-Key")
        )
        try:
            analysis_request = queue_manual_analysis(
                project_id=project_id,
                actor=request.user,
                idempotency_key=idempotency_key,
            )
        except (
            AIWorkspaceConflictError,
            AIWorkspaceNotFoundError,
            AIWorkspacePermissionError,
        ) as error:
            _translate_service_error(error)
        return Response(
            AIAnalysisRequestSerializer(analysis_request).data,
            status=status.HTTP_202_ACCEPTED,
        )


class AIAnalysisDetailView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_analysis_retrieve",
        responses={200: AIAnalysisRequestSerializer},
    )
    def get(self, request, project_id, request_id):
        try:
            record = get_analysis_request(
                project_id=project_id,
                request_id=request_id,
                actor=request.user,
            )
        except (AIWorkspaceNotFoundError, AIWorkspacePermissionError) as error:
            _translate_service_error(error)
        return Response(AIAnalysisRequestSerializer(record).data)


class AIProposalCollectionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_proposal_list",
        responses={200: AIProposalPageSerializer},
    )
    def get(self, request, project_id):
        try:
            records = list_ai_proposals(project_id=project_id, actor=request.user)
        except (AIWorkspaceNotFoundError, AIWorkspacePermissionError) as error:
            _translate_service_error(error)
        paginator = AIWorkspacePagination()
        page = paginator.paginate_queryset(records, request, view=self)
        return paginator.get_paginated_response(
            AIProposalSerializer(page, many=True).data
        )


class AIProposalDetailView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_proposal_retrieve",
        responses={200: AIProposalSerializer},
    )
    def get(self, request, proposal_id):
        try:
            proposal = get_ai_proposal(proposal_id=proposal_id, actor=request.user)
        except (AIWorkspaceNotFoundError, AIWorkspacePermissionError) as error:
            _translate_service_error(error)
        return Response(AIProposalSerializer(proposal).data)


class AIProposalActionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]
    action = None

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_proposal_action",
        request=EmptyRequestSerializer,
        responses={200: AIProposalSerializer},
    )
    def post(self, request, proposal_id):
        serializer = EmptyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            if self.action == "accept":
                proposal = apply_ai_proposal(
                    proposal_id=proposal_id,
                    actor=request.user,
                )
            else:
                proposal = reject_ai_proposal(
                    proposal_id=proposal_id,
                    actor=request.user,
                )
        except (
            AIWorkspaceConflictError,
            AIWorkspaceNotFoundError,
            AIWorkspacePermissionError,
            DjangoValidationError,
        ) as error:
            _translate_service_error(error)
        return Response(AIProposalSerializer(proposal).data)


class AIProposalAcceptView(AIProposalActionView):
    action = "accept"

    @extend_schema(
        operation_id="ai_proposal_accept",
        request=EmptyRequestSerializer,
        responses={200: AIProposalSerializer},
    )
    def post(self, request, proposal_id):
        return super().post(request, proposal_id)


class AIProposalRejectView(AIProposalActionView):
    action = "reject"

    @extend_schema(
        operation_id="ai_proposal_reject",
        request=EmptyRequestSerializer,
        responses={200: AIProposalSerializer},
    )
    def post(self, request, proposal_id):
        return super().post(request, proposal_id)


class AIProposalApplyEditedView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["ai_assistant"],
        operation_id="ai_proposal_apply_edited",
        request=ApplyEditedProposalSerializer,
        responses={200: AIProposalSerializer},
    )
    def post(self, request, proposal_id):
        serializer = ApplyEditedProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = apply_ai_proposal(
                proposal_id=proposal_id,
                actor=request.user,
                payload=serializer.validated_data["final_payload"],
            )
        except (
            AIWorkspaceConflictError,
            AIWorkspaceNotFoundError,
            AIWorkspacePermissionError,
            DjangoValidationError,
        ) as error:
            _translate_service_error(error)
        return Response(AIProposalSerializer(proposal).data)
