from django.urls import path

from .verification.views import ConfirmVerificationView, ResendVerificationView

app_name = "accounts_verification"
urlpatterns = [
    path(
        "email-verification/resend/",
        ResendVerificationView.as_view(),
        name="email-verification-resend",
    ),
    path(
        "email-verification/confirm/",
        ConfirmVerificationView.as_view(),
        name="email-verification-confirm",
    ),
]
