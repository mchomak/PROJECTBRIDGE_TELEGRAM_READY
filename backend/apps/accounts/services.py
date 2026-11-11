import hashlib
import secrets
from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import EmailVerificationToken, User

EMAIL_VERIFICATION_TTL = timedelta(hours=24)


class InvalidVerificationToken(Exception):
    def __init__(self):
        super().__init__("The verification token is invalid or expired.")


def _validated_email(email):
    normalized_email = User.objects.normalize_email(email)
    try:
        return User._meta.get_field("email").clean(normalized_email, None)
    except ValidationError as exc:
        raise ValidationError({"email": exc.messages}) from exc


def _issue_verification_token(user):
    now = timezone.now()
    EmailVerificationToken.objects.filter(
        user=user,
        used_at__isnull=True,
    ).update(used_at=now)

    raw_token = secrets.token_urlsafe(32)
    token_digest = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    EmailVerificationToken.objects.create(
        user=user,
        token_hash=token_digest,
        expires_at=now + EMAIL_VERIFICATION_TTL,
    )
    return raw_token


def _send_verification_email(email, raw_token):
    frontend_base_url = getattr(
        settings, "FRONTEND_BASE_URL", "http://localhost:5173"
    ).rstrip("/")
    confirmation_url = f"{frontend_base_url}/verify-email#token={raw_token}"
    send_mail(
        subject="Confirm your ProjectBridge email",
        message=(
            f"Confirm your email address by opening this link:\n\n{confirmation_url}\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def register_user(email, password):
    normalized_email = _validated_email(email)
    user_candidate = User(email=normalized_email)
    validate_password(password, user_candidate)

    with transaction.atomic():
        if User.objects.filter(email=normalized_email).exists():
            raise ValidationError(
                {"email": ["An account with this email already exists."]}
            )

        try:
            with transaction.atomic():
                user = User.objects.create_user(normalized_email, password)
        except IntegrityError as exc:
            if User.objects.filter(email=normalized_email).exists():
                raise ValidationError(
                    {"email": ["An account with this email already exists."]}
                ) from exc
            raise

        raw_token = _issue_verification_token(user)
        transaction.on_commit(partial(_send_verification_email, user.email, raw_token))

    return user


def authenticate_user(email, password):
    if not isinstance(email, str) or not isinstance(password, str):
        return None
    normalized_email = User.objects.normalize_email(email)
    if not normalized_email:
        return None
    return authenticate(username=normalized_email, password=password)


def resend_verification(email):
    normalized_email = User.objects.normalize_email(email)
    if not normalized_email:
        return None

    with transaction.atomic():
        user = User.objects.select_for_update().filter(email=normalized_email).first()
        if user is None or user.email_verified_at is not None:
            return None

        raw_token = _issue_verification_token(user)
        transaction.on_commit(partial(_send_verification_email, user.email, raw_token))

    return None


def confirm_verification(raw_token):
    if not isinstance(raw_token, str) or not raw_token:
        raise InvalidVerificationToken()

    token_digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    try:
        with transaction.atomic():
            token = (
                EmailVerificationToken.objects.select_for_update()
                .select_related("user")
                .get(token_hash=token_digest)
            )
            now = timezone.now()
            if token.used_at is not None or token.expires_at <= now:
                raise InvalidVerificationToken()

            token.used_at = now
            token.save(update_fields=["used_at"])

            user = token.user
            if user.email_verified_at is None:
                user.email_verified_at = now
                user.save(update_fields=["email_verified_at", "updated_at"])
            return user
    except EmailVerificationToken.DoesNotExist:
        raise InvalidVerificationToken() from None
