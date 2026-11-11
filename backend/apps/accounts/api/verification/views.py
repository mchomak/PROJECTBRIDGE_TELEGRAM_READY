from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.services import (
    InvalidVerificationToken,
    confirm_verification,
    resend_verification,
)

from ..core.serializers import ErrorEnvelopeSerializer
from .serializers import (
    ConfirmVerificationRequestSerializer,
    ConfirmVerificationResponseSerializer,
    ResendVerificationRequestSerializer,
    ResendVerificationResponseSerializer,
)

RESEND_DETAIL = "If an unverified account exists, a verification email has been sent."


@method_decorator(csrf_protect, name="dispatch")
class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend"

    @extend_schema(
        request=ResendVerificationRequestSerializer,
        responses={
            status.HTTP_202_ACCEPTED: ResendVerificationResponseSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        serializer = ResendVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        if request.user.is_authenticated:
            if email is None:
                email = request.user.email
            else:
                normalized_email = get_user_model().objects.normalize_email(email)
                if normalized_email != request.user.email:
                    raise PermissionDenied(
                        "You may request verification only for your email."
                    )
        elif email is None:
            raise ValidationError({"email": ["This field is required."]})

        resend_verification(email)
        return Response(
            {"detail": RESEND_DETAIL},
            status=status.HTTP_202_ACCEPTED,
        )


@method_decorator(csrf_protect, name="dispatch")
class ConfirmVerificationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "confirm"

    @extend_schema(
        request=ConfirmVerificationRequestSerializer,
        responses={
            status.HTTP_200_OK: ConfirmVerificationResponseSerializer,
            status.HTTP_400_BAD_REQUEST: ErrorEnvelopeSerializer,
            status.HTTP_403_FORBIDDEN: ErrorEnvelopeSerializer,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ErrorEnvelopeSerializer,
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        serializer = ConfirmVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = confirm_verification(serializer.validated_data["token"])
        except InvalidVerificationToken:
            raise ValidationError(
                {"token": ["The verification token is invalid or expired."]}
            ) from None

        return Response(
            ConfirmVerificationResponseSerializer(
                {
                    "email_verified": user.email_verified_at is not None,
                    "email_verified_at": user.email_verified_at,
                }
            ).data,
            status=status.HTTP_200_OK,
        )
