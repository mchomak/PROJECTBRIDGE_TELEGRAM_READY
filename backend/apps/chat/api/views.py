from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, Throttled, ValidationError
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from apps.accounts.api.core.serializers import ErrorEnvelopeSerializer
from apps.chat.services import (
    ChatMessageConflictError,
    ChatMessageNotFoundError,
    ChatMessageRateLimitError,
    list_messages,
    send_message,
)

from .serializers import (
    MessageCreateSerializer,
    MessagePageResponseSerializer,
    MessageResponseSerializer,
)


class MessageConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The message ID or project state conflicts with this request."
    default_code = "conflict"


def _raise_chat_error(error):
    if isinstance(error, ChatMessageNotFoundError):
        raise NotFound("Project chat is unavailable to your account.") from None
    if isinstance(error, ChatMessageConflictError):
        raise MessageConflict from None
    if isinstance(error, ChatMessageRateLimitError):
        raise Throttled(
            detail="Chat send rate limit exceeded. Try again in the next minute."
        ) from None
    if isinstance(error, DjangoValidationError):
        detail = (
            error.message_dict
            if hasattr(error, "message_dict")
            else {"non_field_errors": error.messages}
        )
        raise ValidationError(detail) from None
    raise error


def _message_page_link(request, *, project_id, cursor, page_size):
    if cursor is None:
        return None
    params = request.query_params.copy()
    params["cursor"] = cursor
    params["page_size"] = str(page_size)
    path = reverse("projects:chat:project-messages", args=[project_id])
    return request.build_absolute_uri(f"{path}?{params.urlencode()}")


class ProjectMessagesView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["chat"],
        operation_id="project_messages_list",
        parameters=[
            OpenApiParameter(
                "cursor",
                OpenApiTypes.STR,
                required=False,
                description="Stable history cursor.",
            ),
            OpenApiParameter(
                "page_size",
                OpenApiTypes.INT,
                required=False,
                description="Messages per page (default 50, maximum 100).",
            ),
        ],
        responses={
            200: MessagePageResponseSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        raw_page_size = request.query_params.get("page_size", "50")
        try:
            page_size = int(raw_page_size)
        except (TypeError, ValueError):
            raise ValidationError({"page_size": "Enter a positive integer."}) from None
        if page_size < 1:
            raise ValidationError({"page_size": "Page size must be positive."})
        page_size = min(page_size, 100)
        try:
            page = list_messages(
                project_id=project_id,
                actor=request.user,
                cursor=request.query_params.get("cursor"),
                limit=page_size,
            )
        except (
            ChatMessageNotFoundError,
            ChatMessageConflictError,
            ChatMessageRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_chat_error(exc)

        payload = {
            "next": _message_page_link(
                request,
                project_id=project_id,
                cursor=page.next_cursor,
                page_size=page_size,
            ),
            "previous": _message_page_link(
                request,
                project_id=project_id,
                cursor=page.previous_cursor,
                page_size=page_size,
            ),
            "results": MessageResponseSerializer(page.results, many=True).data,
        }
        return Response(MessagePageResponseSerializer(payload).data)

    @extend_schema(
        tags=["chat"],
        operation_id="project_messages_create",
        request=MessageCreateSerializer,
        responses={
            200: MessageResponseSerializer,
            201: MessageResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, project_id):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = send_message(
                project_id=project_id,
                actor=request.user,
                client_message_id=serializer.validated_data["client_message_id"],
                content=serializer.validated_data["content"],
            )
        except (
            ChatMessageNotFoundError,
            ChatMessageConflictError,
            ChatMessageRateLimitError,
            DjangoValidationError,
        ) as exc:
            _raise_chat_error(exc)
        response_status = (
            status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        )
        return Response(
            MessageResponseSerializer(result.message).data,
            status=response_status,
        )
