import json
from uuid import UUID

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import (
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.test import APIRequestFactory

from apps.common.api.errors import api_exception_handler, csrf_failure


def test_api_exception_handler_wraps_validation_errors_in_stable_envelope():
    request = APIRequestFactory().post("/api/v1/auth/register/", {}, format="json")

    response = api_exception_handler(
        ValidationError({"email": ["Enter a valid email address."]}),
        {"request": request},
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["detail"] == "Request validation failed."
    assert response.data["errors"] == {"email": ["Enter a valid email address."]}
    UUID(response.data["request_id"])


@pytest.mark.parametrize(
    ("exception", "status_code", "error_code"),
    [
        (NotAuthenticated(), 401, "unauthenticated"),
        (PermissionDenied(), 403, "permission_denied"),
    ],
)
def test_api_exception_handler_maps_authentication_and_permission_errors(
    exception,
    status_code,
    error_code,
):
    request = APIRequestFactory().get("/api/v1/auth/me/")

    response = api_exception_handler(exception, {"request": request})

    assert response.status_code == status_code
    assert response.data["code"] == error_code
    assert response.data["errors"] is None
    UUID(response.data["request_id"])


def test_csrf_failure_returns_json_envelope_without_echoing_failure_reason():
    request = RequestFactory().post("/api/v1/auth/register/")
    response = csrf_failure(request, "secret cookie value rejected")

    payload = json.loads(response.content)
    assert response.status_code == 403
    assert response["Content-Type"] == "application/json"
    assert payload["code"] == "csrf_failed"
    assert payload["detail"] == "CSRF verification failed."
    assert payload["errors"] is None
    assert "secret cookie value" not in response.content.decode()
    UUID(payload["request_id"])


def test_api_exception_handler_hides_unexpected_exception_details(caplog):
    request = APIRequestFactory().get("/api/v1/auth/me/")
    secret = "raw-verification-token"

    response = api_exception_handler(
        RuntimeError(secret),
        {"request": request},
    )

    assert response.status_code == 500
    assert response.data["code"] == "internal_error"
    assert response.data["detail"] == "An unexpected error occurred."
    assert secret not in json.dumps(response.data)
    assert secret not in caplog.text
    UUID(response.data["request_id"])
