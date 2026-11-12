from uuid import uuid4

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from apps.accounts.api.core.serializers import ErrorEnvelopeSerializer
from apps.invitations.services import (
    InvitationEmailMismatchError,
    InvitationEmailUnverifiedError,
    InvitationNotFoundError,
    InvitationPermissionError,
    InvitationRateLimitError,
    InvitationStateConflictError,
    InvitationUnavailableError,
    accept_invitation,
    create_invitation,
    enforce_invitation_preview_limit,
    get_project_invitations,
    preview_invitation,
    revoke_invitation,
)

from .serializers import (
    InvitationAcceptanceResponseSerializer,
    InvitationCreateSerializer,
    InvitationListResponseSerializer,
    InvitationPreviewRequestSerializer,
    InvitationPreviewResponseSerializer,
    InvitationResponseSerializer,
)


class InvitationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The invitation cannot be changed in its current state."
    default_code = "conflict"


class InvitationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _raise_invitation_error(error):
    if isinstance(error, InvitationNotFoundError):
        raise NotFound("Project invitation not found.") from error
    if isinstance(error, InvitationPermissionError):
        raise PermissionDenied(
            "Only the project executor can manage invitations."
        ) from error
    if isinstance(error, InvitationStateConflictError):
        raise InvitationConflict from error
    if isinstance(error, InvitationRateLimitError):
        raise Throttled(
            detail="Invitation rate limit exceeded. Try again later."
        ) from error
    if isinstance(error, DjangoValidationError):
        detail = (
            error.message_dict
            if hasattr(error, "message_dict")
            else {"non_field_errors": error.messages}
        )
        raise ValidationError(detail) from error
    raise error


def _invitation_state_error_response(error, *, status_code=None):
    return _invitation_error_response(
        code=error.code,
        detail=error.detail,
        status_code=status_code or error.status_code,
    )


def _invitation_error_response(*, code, detail, status_code):
    return Response(
        {
            "code": code,
            "detail": detail,
            "errors": None,
            "request_id": str(uuid4()),
        },
        status=status_code,
    )


class ProjectInvitationListCreateView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["invitations"],
        operation_id="project_invitations_list",
        responses={
            200: InvitationListResponseSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        try:
            invitations = get_project_invitations(
                project_id=project_id,
                actor=request.user,
            )
        except (
            InvitationNotFoundError,
            InvitationPermissionError,
            InvitationStateConflictError,
            InvitationRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_invitation_error(exc)

        paginator = InvitationPagination()
        page = paginator.paginate_queryset(invitations, request, view=self)
        return paginator.get_paginated_response(
            InvitationResponseSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["invitations"],
        operation_id="project_invitations_create",
        request=InvitationCreateSerializer,
        responses={
            201: InvitationResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, project_id):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = create_invitation(
                project_id=project_id,
                actor=request.user,
                invited_email=serializer.validated_data["invited_email"],
            )
        except (
            InvitationNotFoundError,
            InvitationPermissionError,
            InvitationStateConflictError,
            InvitationRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_invitation_error(exc)
        return Response(
            InvitationResponseSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectInvitationRevokeView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]
    serializer_class = InvitationResponseSerializer

    @extend_schema(
        tags=["invitations"],
        operation_id="project_invitations_revoke",
        responses={
            200: InvitationResponseSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, project_id, invitation_id):
        try:
            invitation = revoke_invitation(
                project_id=project_id,
                actor=request.user,
                invitation_id=invitation_id,
            )
        except (
            InvitationNotFoundError,
            InvitationPermissionError,
            InvitationStateConflictError,
            InvitationRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_invitation_error(exc)
        return Response(InvitationResponseSerializer(invitation).data)


class PublicInvitationPreviewView(CsrfSanitizingAPIView):
    permission_classes = [RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["invitations"],
        operation_id="invitation_preview",
        request=InvitationPreviewRequestSerializer,
        responses={
            200: InvitationPreviewResponseSerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
            410: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        try:
            enforce_invitation_preview_limit(
                client_ip=request.META.get("REMOTE_ADDR"),
            )
            serializer = InvitationPreviewRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            preview = preview_invitation(serializer.validated_data["token"])
        except InvitationUnavailableError as exc:
            return _invitation_state_error_response(exc)
        except (
            InvitationNotFoundError,
            InvitationRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_invitation_error(exc)

        return Response(InvitationPreviewResponseSerializer(preview).data)


class InvitationAcceptView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["invitations"],
        operation_id="invitation_accept",
        request=InvitationPreviewRequestSerializer,
        responses={
            200: InvitationAcceptanceResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
            410: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        serializer = InvitationPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = accept_invitation(
                actor=request.user,
                raw_token=serializer.validated_data["token"],
            )
        except (InvitationEmailMismatchError, InvitationEmailUnverifiedError) as exc:
            code = (
                "email_mismatch"
                if isinstance(exc, InvitationEmailMismatchError)
                else "email_unverified"
            )
            detail = (
                "Sign in with the verified email address invited to this project."
                if code == "email_mismatch"
                else "Verify your email address before accepting this invitation."
            )
            return _invitation_error_response(
                code=code,
                detail=detail,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except InvitationUnavailableError as exc:
            return _invitation_state_error_response(exc)
        except (
            InvitationNotFoundError,
            InvitationPermissionError,
            InvitationStateConflictError,
            InvitationRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_invitation_error(exc)

        return Response(
            InvitationAcceptanceResponseSerializer(
                {
                    "invitation_id": invitation.pk,
                    "project_id": invitation.project_id,
                    "status": invitation.status,
                }
            ).data
        )
