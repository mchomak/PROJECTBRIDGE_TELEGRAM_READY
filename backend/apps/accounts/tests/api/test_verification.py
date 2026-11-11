import hashlib
import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient


@pytest.mark.django_db(transaction=True)
def test_resend_is_enumeration_resistant_and_delivers_hashed_fragment_link(
    capsys, caplog
):
    from apps.accounts.models import EmailVerificationToken

    user_model = get_user_model()
    unverified_user = user_model.objects.create_user(
        email="waiting@example.com",
        password="correct horse battery staple",
    )
    verified_user = user_model.objects.create_user(
        email="verified@example.com",
        password="correct horse battery staple",
    )
    verified_user.email_verified_at = timezone.now()
    verified_user.save(update_fields=["email_verified_at"])

    client = APIClient(enforce_csrf_checks=False)
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        FRONTEND_BASE_URL="https://app.example",
    ):
        missing_response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": "missing@example.com"},
            format="json",
        )
        verified_response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": verified_user.email},
            format="json",
        )
        eligible_response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": unverified_user.email},
            format="json",
        )

    responses = [missing_response, verified_response, eligible_response]
    assert [response.status_code for response in responses] == [202, 202, 202]
    neutral_detail = (
        "If an unverified account exists, a verification email has been sent."
    )
    expected_responses = [{"detail": neutral_detail}] * 3
    assert [response.json() for response in responses] == expected_responses

    console_email = capsys.readouterr().out
    token_match = re.search(
        r"https://app\.example/verify-email#token=([A-Za-z0-9_-]+)", console_email
    )
    assert token_match is not None
    raw_token = token_match.group(1)
    assert raw_token not in eligible_response.content.decode()
    assert raw_token not in caplog.text

    token_record = EmailVerificationToken.objects.get(user=unverified_user)
    expected_digest = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    assert token_record.token_hash == expected_digest
    assert raw_token not in token_record.token_hash
    assert not EmailVerificationToken.objects.filter(user=verified_user).exists()
    assert not EmailVerificationToken.objects.filter(
        user__email="missing@example.com"
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_authenticated_resend_cannot_target_another_email():
    user_model = get_user_model()
    session_user = user_model.objects.create_user(
        email="session@example.com",
        password="correct horse battery staple",
    )
    other_user = user_model.objects.create_user(
        email="other@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()

    client = APIClient(enforce_csrf_checks=False)
    client.force_login(session_user)
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        mismatch_response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": other_user.email},
            format="json",
        )
        own_response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": session_user.email},
            format="json",
        )

    assert mismatch_response.status_code == 403
    assert own_response.status_code == 202
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [session_user.email]


@pytest.mark.django_db(transaction=True)
def test_authenticated_resend_defaults_to_the_session_email():
    session_user = get_user_model().objects.create_user(
        email="session-default@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()

    client = APIClient(enforce_csrf_checks=False)
    client.force_login(session_user)
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {},
            format="json",
        )

    assert response.status_code == 202
    assert mail.outbox[0].to == [session_user.email]


@pytest.mark.django_db(transaction=True)
def test_anonymous_resend_requires_csrf_token():
    from apps.accounts.models import EmailVerificationToken

    user = get_user_model().objects.create_user(
        email="csrf@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()

    client = APIClient(enforce_csrf_checks=True)
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": user.email},
            format="json",
        )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    assert not EmailVerificationToken.objects.filter(user=user).exists()
    assert mail.outbox == []


@pytest.mark.django_db(transaction=True)
def test_confirmation_verifies_user_and_returns_verification_timestamp():
    from apps.accounts.models import EmailVerificationToken
    from apps.accounts.services import resend_verification

    user = get_user_model().objects.create_user(
        email="confirm@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FRONTEND_BASE_URL="https://app.example",
    ):
        resend_verification(user.email)
        raw_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[0].body).group(1)
        response = APIClient().post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": raw_token},
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["email_verified"] is True
    user.refresh_from_db()
    returned_timestamp = parse_datetime(response.json()["email_verified_at"])
    assert user.email_verified_at is not None
    assert returned_timestamp == user.email_verified_at
    token_record = EmailVerificationToken.objects.get(
        token_hash=hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    )
    assert token_record.used_at is not None


@pytest.mark.django_db(transaction=True)
def test_anonymous_confirmation_requires_csrf_token():
    from apps.accounts.services import resend_verification

    user = get_user_model().objects.create_user(
        email="confirm-csrf@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        resend_verification(user.email)
        raw_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[0].body).group(1)
        response = APIClient(enforce_csrf_checks=True).post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": raw_token},
            format="json",
        )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"
    user.refresh_from_db()
    assert user.email_verified_at is None


@pytest.mark.django_db(transaction=True)
def test_browser_can_resend_and_confirm_with_bootstrapped_csrf_token():
    user = get_user_model().objects.create_user(
        email="csrf-valid@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()
    client = APIClient(enforce_csrf_checks=True)
    client.defaults["REMOTE_ADDR"] = "198.51.100.19"
    csrf_response = client.get("/api/v1/auth/csrf/")
    csrf_token = csrf_response.data["csrf_token"]
    csrf_headers = {"HTTP_X_CSRFTOKEN": csrf_token}

    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        resend_response = client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": user.email},
            format="json",
            **csrf_headers,
        )
        raw_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[0].body).group(1)
        confirm_response = client.post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": raw_token},
            format="json",
            **csrf_headers,
        )

    assert csrf_response.status_code == 200
    assert client.cookies["csrftoken"].value
    assert resend_response.status_code == 202
    assert confirm_response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_confirmation_accepts_token_only_in_json_body():
    from apps.accounts.models import EmailVerificationToken
    from apps.accounts.services import resend_verification

    user = get_user_model().objects.create_user(
        email="json-token@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        resend_verification(user.email)
        raw_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[0].body).group(1)

    path = "/api/v1/auth/email-verification/confirm/"
    client = APIClient()
    query_response = client.post(
        f"{path}?token={raw_token}",
        {},
        format="json",
    )
    form_response = client.post(path, {"token": raw_token})

    assert query_response.status_code == 400
    assert query_response.data["errors"]["token"]
    assert form_response.status_code == 415
    user.refresh_from_db()
    assert user.email_verified_at is None
    assert EmailVerificationToken.objects.get(user=user).used_at is None


@pytest.mark.django_db(transaction=True)
def test_resend_and_confirm_use_separate_scoped_throttles():
    client = APIClient()
    client.defaults["REMOTE_ADDR"] = "198.51.100.17"
    cache.clear()
    resend_responses = [
        client.post(
            "/api/v1/auth/email-verification/resend/",
            {"email": "missing@example.com"},
            format="json",
        )
        for _ in range(4)
    ]
    confirm_responses = [
        client.post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": "unknown-token"},
            format="json",
        )
        for _ in range(11)
    ]

    assert [response.status_code for response in resend_responses] == [
        202,
        202,
        202,
        429,
    ]
    assert resend_responses[-1].json()["code"] == "throttled"
    assert [response.status_code for response in confirm_responses] == [
        *([400] * 10),
        429,
    ]
    assert confirm_responses[-1].json()["code"] == "throttled"
    cache.clear()


@pytest.mark.django_db(transaction=True)
def test_invalid_expired_and_reused_tokens_have_the_same_generic_api_error(
    caplog,
):
    from apps.accounts.models import EmailVerificationToken
    from apps.accounts.services import resend_verification

    user_model = get_user_model()
    expired_user = user_model.objects.create_user(
        email="expired-api@example.com",
        password="correct horse battery staple",
    )
    reused_user = user_model.objects.create_user(
        email="reused-api@example.com",
        password="correct horse battery staple",
    )
    mail.outbox.clear()
    client = APIClient()
    client.defaults["REMOTE_ADDR"] = "198.51.100.18"
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ):
        resend_verification(expired_user.email)
        resend_verification(reused_user.email)
        expired_token = re.search(
            r"#token=([A-Za-z0-9_-]+)", mail.outbox[0].body
        ).group(1)
        reused_token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[1].body).group(
            1
        )

        expired_record = EmailVerificationToken.objects.get(
            token_hash=hashlib.sha256(expired_token.encode("ascii")).hexdigest()
        )
        expired_record.expires_at = timezone.now() - timedelta(seconds=1)
        expired_record.save(update_fields=["expires_at"])

        invalid_response = client.post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": "unknown-token"},
            format="json",
        )
        expired_response = client.post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": expired_token},
            format="json",
        )
        first_confirm_response = client.post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": reused_token},
            format="json",
        )
        reused_response = client.post(
            "/api/v1/auth/email-verification/confirm/",
            {"token": reused_token},
            format="json",
        )

    assert first_confirm_response.status_code == 200
    failures = [invalid_response, expired_response, reused_response]
    assert [response.status_code for response in failures] == [400, 400, 400]
    error_shapes = [
        {
            "code": response.data["code"],
            "detail": response.data["detail"],
            "errors": response.data["errors"],
        }
        for response in failures
    ]
    assert (
        error_shapes
        == [
            {
                "code": "validation_error",
                "detail": "Request validation failed.",
                "errors": {"token": ["The verification token is invalid or expired."]},
            }
        ]
        * 3
    )
    assert expired_token not in expired_response.content.decode()
    assert reused_token not in reused_response.content.decode()
    assert expired_token not in caplog.text
    assert reused_token not in caplog.text

    expired_user.refresh_from_db()
    reused_user.refresh_from_db()
    assert expired_user.email_verified_at is None
    verified_at_before_reuse = parse_datetime(
        first_confirm_response.data["email_verified_at"]
    )
    assert reused_user.email_verified_at == verified_at_before_reuse


def test_verification_endpoints_document_request_success_and_error_schemas():
    schema_response = APIClient().get("/api/schema/")
    assert schema_response.status_code == 200
    schema = schema_response.data
    paths = schema["paths"]
    expected_operations = {
        "/api/v1/auth/email-verification/resend/": {
            "request_field": "email",
            "success_status": "202",
            "success_field": "detail",
        },
        "/api/v1/auth/email-verification/confirm/": {
            "request_field": "token",
            "success_status": "200",
            "success_field": "email_verified",
        },
    }

    for path, expectations in expected_operations.items():
        operation = paths[path]["post"]
        request_schema_ref = operation["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        request_schema_name = request_schema_ref.rsplit("/", maxsplit=1)[-1]
        assert (
            expectations["request_field"]
            in schema["components"]["schemas"][request_schema_name]["properties"]
        )

        success_response = operation["responses"][expectations["success_status"]]
        response_schema_ref = success_response["content"]["application/json"]["schema"][
            "$ref"
        ]
        response_schema_name = response_schema_ref.rsplit("/", maxsplit=1)[-1]
        assert (
            expectations["success_field"]
            in schema["components"]["schemas"][response_schema_name]["properties"]
        )

        for error_status in ("400", "403", "429"):
            error_response = operation["responses"][error_status]
            error_schema_ref = error_response["content"]["application/json"]["schema"][
                "$ref"
            ]
            error_schema_name = error_schema_ref.rsplit("/", maxsplit=1)[-1]
            assert set(
                schema["components"]["schemas"][error_schema_name]["properties"]
            ) == {
                "code",
                "detail",
                "errors",
                "request_id",
            }
