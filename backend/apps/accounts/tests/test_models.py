import re
from base64 import urlsafe_b64decode
from datetime import timedelta
from hashlib import sha256
from importlib import import_module
from uuid import UUID

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import override_settings


def test_accounts_user_is_the_configured_authentication_model():
    assert settings.AUTH_USER_MODEL == "accounts.User"

    local_settings = import_module("config.settings.local")
    assert local_settings.AUTH_USER_MODEL == "accounts.User"

    from django.db.migrations.loader import MigrationLoader

    migration_loader = MigrationLoader(None, ignore_no_migrations=True)
    assert ("accounts", "0001_initial") in migration_loader.disk_migrations


@pytest.mark.django_db
def test_user_manager_normalizes_email_and_creates_uuid_account():
    user = get_user_model().objects.create_user(
        email="  Alice.Example@Example.COM  ",
        password="correct horse battery staple",
    )

    assert user.email == "alice.example@example.com"
    assert isinstance(user.pk, UUID)
    assert user.email_verified_at is None
    assert user.first_name == ""
    assert user.last_name == ""


@pytest.mark.django_db(transaction=True)
def test_register_user_normalizes_email_hashes_password_and_sends_hashed_token(
    caplog,
):
    from apps.accounts.models import EmailVerificationToken
    from apps.accounts.services import register_user

    mail.outbox.clear()
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FRONTEND_BASE_URL="https://app.example",
    ):
        user = register_user(
            "  Alice.Example@Example.COM  ", "correct horse battery staple"
        )

    assert user.email == "alice.example@example.com"
    assert user.check_password("correct horse battery staple")
    assert user.password != "correct horse battery staple"
    assert len(mail.outbox) == 1

    match = re.search(r"/verify-email#token=([A-Za-z0-9_-]+)", mail.outbox[0].body)
    assert match is not None
    raw_token = match.group(1)
    decoded_token = urlsafe_b64decode(raw_token + "=" * (-len(raw_token) % 4))
    assert len(decoded_token) == 32

    token = EmailVerificationToken.objects.get(user=user)
    assert token.token_hash == sha256(raw_token.encode("ascii")).hexdigest()
    assert raw_token not in token.token_hash
    assert (
        timedelta(hours=23) < token.expires_at - token.created_at <= timedelta(hours=24)
    )
    assert raw_token not in caplog.text

    with pytest.raises(ValidationError):
        register_user("ALICE.EXAMPLE@example.com", "correct horse battery staple")


@pytest.mark.django_db
def test_authenticate_user_normalizes_email_and_rejects_wrong_password():
    from apps.accounts.services import authenticate_user

    user = get_user_model().objects.create_user(
        email="person@example.com",
        password="correct horse battery staple",
    )

    assert (
        authenticate_user("  PERSON@EXAMPLE.COM ", "correct horse battery staple")
        == user
    )
    assert user.email_verified_at is None
    assert authenticate_user("person@example.com", "wrong password") is None


@pytest.mark.django_db(transaction=True)
def test_resend_rotates_tokens_and_confirmation_expires_and_consumes_once():
    from django.utils import timezone

    from apps.accounts.models import EmailVerificationToken
    from apps.accounts.services import (
        InvalidVerificationToken,
        confirm_verification,
        resend_verification,
    )

    mail.outbox.clear()
    user = get_user_model().objects.create_user(email="person@example.com")

    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FRONTEND_BASE_URL="https://app.example",
    ):
        resend_verification(" PERSON@EXAMPLE.COM ")
        first_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[0].body).group(
            1
        )
        resend_verification(user.email)
        second_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[1].body).group(
            1
        )

        first_record = EmailVerificationToken.objects.get(
            token_hash=sha256(first_token.encode("ascii")).hexdigest()
        )
        second_record = EmailVerificationToken.objects.get(
            token_hash=sha256(second_token.encode("ascii")).hexdigest()
        )
        assert first_token != second_token
        assert first_record.used_at is not None
        assert second_record.used_at is None
        assert (
            EmailVerificationToken.objects.filter(
                user=user,
                used_at__isnull=True,
            ).count()
            == 1
        )

        with pytest.raises(InvalidVerificationToken) as rotated:
            confirm_verification(first_token)
        verified_user = confirm_verification(second_token)
        assert verified_user.email_verified_at is not None
        assert verified_user == user

        with pytest.raises(InvalidVerificationToken) as reused:
            confirm_verification(second_token)
        assert str(rotated.value) == str(reused.value)
        assert resend_verification(user.email) is None
        assert resend_verification("missing@example.com") is None

        expired_user = get_user_model().objects.create_user(email="expired@example.com")
        resend_verification(expired_user.email)
        expired_token = re.search(
            r"#token=([A-Za-z0-9_-]+)", mail.outbox[2].body
        ).group(1)
        expired_record = EmailVerificationToken.objects.get(
            token_hash=sha256(expired_token.encode("ascii")).hexdigest()
        )
        expired_record.expires_at = timezone.now() - timedelta(seconds=1)
        expired_record.save(update_fields=["expires_at"])

        with pytest.raises(InvalidVerificationToken) as expired:
            confirm_verification(expired_token)
        assert str(rotated.value) == str(expired.value)
        expired_user.refresh_from_db()
        assert expired_user.email_verified_at is None


@pytest.mark.django_db
def test_register_user_applies_django_password_validators():
    from apps.accounts.services import register_user

    invalid_credentials = [
        ("short@example.com", "short"),
        ("common@example.com", "password"),
        ("numeric@example.com", "12345678"),
        ("alice@example.com", "alice@example.com"),
    ]
    for email, password in invalid_credentials:
        with pytest.raises(ValidationError):
            register_user(email, password)


def test_local_auth_runtime_uses_argon_redis_and_initial_throttle_scopes():
    local_settings = import_module("config.settings.local")

    assert local_settings.PASSWORD_HASHERS[:2] == [
        "django.contrib.auth.hashers.Argon2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    ]
    assert (
        local_settings.CACHES["default"]["BACKEND"]
        == "django.core.cache.backends.redis.RedisCache"
    )
    assert local_settings.CACHES["default"]["LOCATION"] == local_settings.REDIS_URL
    assert local_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] == {
        "register": "5/hour",
        "login": "10/minute",
        "resend": "3/hour",
        "confirm": "10/hour",
    }
