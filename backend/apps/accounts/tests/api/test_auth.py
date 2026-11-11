import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    cache.clear()


@pytest.mark.django_db(transaction=True)
def test_registration_creates_unverified_account_without_session():
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": " Alice.Example@Example.COM ",
            "password": "correct horse battery staple",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert response.status_code == 201
    user = get_user_model().objects.get(email="alice.example@example.com")
    assert response.data == {
        "id": str(user.pk),
        "email": "alice.example@example.com",
        "first_name": "",
        "last_name": "",
        "email_verified": False,
        "email_verified_at": None,
    }
    assert user.check_password("correct horse battery staple")
    assert "sessionid" not in response.cookies


@pytest.mark.django_db(transaction=True)
def test_registration_rejects_normalized_duplicate_with_email_field_error():
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")
    headers = {"HTTP_X_CSRFTOKEN": csrf_response.data["csrf_token"]}
    first_response = client.post(
        "/api/v1/auth/register/",
        {"email": "person@example.com", "password": "correct horse battery staple"},
        format="json",
        **headers,
    )

    duplicate_response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "  PERSON@EXAMPLE.COM  ",
            "password": "different horse battery staple",
        },
        format="json",
        **headers,
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 400
    assert duplicate_response.data["code"] == "validation_error"
    assert duplicate_response.data["errors"]["email"]
    assert get_user_model().objects.filter(email="person@example.com").count() == 1


@pytest.mark.django_db
def test_registration_maps_weak_password_validation_to_password_field():
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")

    response = client.post(
        "/api/v1/auth/register/",
        {"email": "person@example.com", "password": "password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["errors"]["password"]


@pytest.mark.django_db
def test_registration_returns_email_field_error_for_invalid_email():
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")

    response = client.post(
        "/api/v1/auth/register/",
        {"email": "not-an-email", "password": "correct horse battery staple"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["errors"]["email"]


def test_openapi_schema_exposes_core_auth_endpoints_and_payloads():
    response = APIClient().get("/api/schema/")

    assert response.status_code == 200
    schema = response.data
    paths = schema["paths"]
    expected_operations = {
        "/api/v1/auth/csrf/": ("get", "200"),
        "/api/v1/auth/register/": ("post", "201"),
        "/api/v1/auth/login/": ("post", "200"),
        "/api/v1/auth/logout/": ("post", "204"),
        "/api/v1/auth/me/": ("get", "200"),
    }

    for path, (method, success_status) in expected_operations.items():
        operation = paths[path][method]
        assert success_status in operation["responses"]

    for path in ("/api/v1/auth/register/", "/api/v1/auth/login/"):
        operation = paths[path]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"]

    register_response = paths["/api/v1/auth/register/"]["post"]["responses"]["201"]
    assert register_response["content"]["application/json"]["schema"]
    assert paths["/api/v1/auth/logout/"]["post"]["responses"]["204"]

    expected_error_responses = {
        "/api/v1/auth/register/": ("400", "403", "429"),
        "/api/v1/auth/login/": ("400", "401", "403", "429"),
        "/api/v1/auth/logout/": ("401", "403"),
        "/api/v1/auth/me/": ("401",),
    }
    for path, statuses in expected_error_responses.items():
        operation_method = (
            "post" if path.endswith(("register/", "login/", "logout/")) else "get"
        )
        operation = paths[path][operation_method]
        for error_status in statuses:
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


@pytest.mark.django_db
def test_login_creates_http_only_session_for_unverified_user():
    user = get_user_model().objects.create_user(
        email="person@example.com",
        password="correct horse battery staple",
    )
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")

    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "correct horse battery staple"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert response.status_code == 200
    assert response.data["id"] == str(user.pk)
    assert response.data["email_verified"] is False
    session_cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert session_cookie["httponly"] is True


@pytest.mark.django_db
def test_login_uses_same_401_for_unknown_email_and_wrong_password():
    get_user_model().objects.create_user(
        email="person@example.com",
        password="correct horse battery staple",
    )
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")
    csrf_header = {"HTTP_X_CSRFTOKEN": csrf_response.data["csrf_token"]}

    unknown_email_response = client.post(
        "/api/v1/auth/login/",
        {"email": "missing@example.com", "password": "correct horse battery staple"},
        format="json",
        **csrf_header,
    )
    wrong_password_response = client.post(
        "/api/v1/auth/login/",
        {"email": "person@example.com", "password": "wrong password"},
        format="json",
        **csrf_header,
    )

    assert unknown_email_response.status_code == 401
    assert wrong_password_response.status_code == 401
    assert unknown_email_response.data["code"] == "unauthenticated"
    assert (
        unknown_email_response.data["detail"] == wrong_password_response.data["detail"]
    )
    assert unknown_email_response.data["errors"] is None
    assert wrong_password_response.data["errors"] is None


@pytest.mark.django_db
def test_current_user_requires_and_returns_the_current_session():
    client = APIClient()

    anonymous_response = client.get("/api/v1/auth/me/")

    assert anonymous_response.status_code == 401
    assert set(anonymous_response.data) == {"code", "detail", "errors", "request_id"}
    assert anonymous_response.data["code"] == "unauthenticated"

    user = get_user_model().objects.create_user(
        email="person@example.com",
        password="correct horse battery staple",
    )
    csrf_response = client.get("/api/v1/auth/csrf/")
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "correct horse battery staple"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    profile_response = client.get("/api/v1/auth/me/")

    assert login_response.status_code == 200
    assert profile_response.status_code == 200
    assert profile_response.data == login_response.data


@pytest.mark.django_db
def test_logout_ends_session_and_returns_no_content():
    user = get_user_model().objects.create_user(
        email="person@example.com",
        password="correct horse battery staple",
    )
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "correct horse battery staple"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )
    csrf_response = client.get("/api/v1/auth/csrf/")

    response = client.post(
        "/api/v1/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert login_response.status_code == 200
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/v1/auth/me/").status_code == 401


@pytest.mark.django_db(transaction=True)
def test_anonymous_browser_write_requires_bootstrapped_csrf_token():
    client = APIClient(enforce_csrf_checks=True)
    payload = {
        "email": "csrf@example.com",
        "password": "correct horse battery staple",
    }

    rejected_response = client.post(
        "/api/v1/auth/register/",
        payload,
        format="json",
    )

    assert rejected_response.status_code == 403
    assert set(rejected_response.data) == {"code", "detail", "errors", "request_id"}
    assert rejected_response.data["errors"] is None

    csrf_response = client.get("/api/v1/auth/csrf/")
    csrf_cookie = csrf_response.cookies[settings.CSRF_COOKIE_NAME]
    assert csrf_response.data["csrf_token"]
    assert not csrf_cookie["httponly"]

    accepted_response = client.post(
        "/api/v1/auth/register/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert accepted_response.status_code == 201


@pytest.mark.django_db(transaction=True)
def test_anonymous_login_requires_bootstrapped_csrf_token():
    user = get_user_model().objects.create_user(
        email="csrf-login@example.com",
        password="correct horse battery staple",
    )
    client = APIClient(enforce_csrf_checks=True)
    payload = {"email": user.email, "password": "correct horse battery staple"}

    rejected_response = client.post(
        "/api/v1/auth/login/",
        payload,
        format="json",
    )

    assert rejected_response.status_code == 403
    assert set(rejected_response.data) == {
        "code",
        "detail",
        "errors",
        "request_id",
    }
    assert rejected_response.data["detail"] == "CSRF verification failed."
    assert "sessionid" not in rejected_response.cookies

    csrf_response = client.get("/api/v1/auth/csrf/")
    accepted_response = client.post(
        "/api/v1/auth/login/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert csrf_response.status_code == 200
    assert csrf_response.cookies[settings.CSRF_COOKIE_NAME]
    assert accepted_response.status_code == 200
    assert accepted_response.data["id"] == str(user.pk)


@pytest.mark.django_db(transaction=True)
def test_authenticated_logout_requires_bootstrapped_csrf_token():
    user = get_user_model().objects.create_user(
        email="csrf-logout@example.com",
        password="correct horse battery staple",
    )
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)

    rejected_response = client.post(
        "/api/v1/auth/logout/",
        {},
        format="json",
    )

    assert rejected_response.status_code == 403
    assert set(rejected_response.data) == {
        "code",
        "detail",
        "errors",
        "request_id",
    }
    assert rejected_response.data["detail"] == "CSRF verification failed."
    assert client.get("/api/v1/auth/me/").status_code == 200

    csrf_response = client.get("/api/v1/auth/csrf/")
    accepted_response = client.post(
        "/api/v1/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )

    assert csrf_response.status_code == 200
    assert accepted_response.status_code == 204
    assert client.get("/api/v1/auth/me/").status_code == 401


@pytest.mark.django_db(transaction=True)
def test_registration_throttle_returns_common_429_envelope():
    cache.clear()
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/")
    payload = {
        "email": "limited@example.com",
        "password": "correct horse battery staple",
    }

    responses = [
        client.post(
            "/api/v1/auth/register/",
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )
        for _ in range(6)
    ]

    assert [response.status_code for response in responses] == [
        201,
        400,
        400,
        400,
        400,
        429,
    ]
    assert responses[-1].data["code"] == "throttled"
    assert set(responses[-1].data) == {"code", "detail", "errors", "request_id"}
