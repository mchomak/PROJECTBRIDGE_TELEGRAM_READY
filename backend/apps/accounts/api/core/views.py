from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.services import authenticate_user, register_user

from .permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from .serializers import (
    CredentialsSerializer,
    CsrfTokenSerializer,
    ErrorEnvelopeSerializer,
    UserSummarySerializer,
)


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CsrfTokenSerializer})
    def get(self, request):
        return Response({"csrf_token": get_token(request._request)})


class RegisterView(CsrfSanitizingAPIView):
    permission_classes = [AllowAny, RequireCsrfForUnsafeRequests]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(
        request=CredentialsSerializer,
        responses={
            201: UserSummarySerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        credentials = CredentialsSerializer(data=request.data)
        credentials.is_valid(raise_exception=True)

        try:
            user = register_user(**credentials.validated_data)
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"password": exc.messages}
            )
            raise ValidationError(detail) from exc

        return Response(
            UserSummarySerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class InvalidCredentials(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid email or password."
    default_code = "unauthenticated"


class LoginView(CsrfSanitizingAPIView):
    permission_classes = [AllowAny, RequireCsrfForUnsafeRequests]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        request=CredentialsSerializer,
        responses={
            200: UserSummarySerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            429: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        credentials = CredentialsSerializer(data=request.data)
        credentials.is_valid(raise_exception=True)
        user = authenticate_user(**credentials.validated_data)
        if user is None:
            raise InvalidCredentials()

        login(request._request, user)
        return Response(UserSummarySerializer(user).data)


class CurrentUserView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser]

    @extend_schema(
        responses={
            200: UserSummarySerializer,
            401: ErrorEnvelopeSerializer,
        }
    )
    def get(self, request):
        return Response(UserSummarySerializer(request.user).data)


class LogoutView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser]

    @extend_schema(
        request=None,
        responses={
            204: None,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)
