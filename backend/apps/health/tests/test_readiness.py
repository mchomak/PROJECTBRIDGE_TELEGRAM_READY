from unittest.mock import patch

from rest_framework.test import APIClient

from apps.health.checks import check_readiness


@patch("apps.health.checks.connection.cursor")
@patch("apps.health.checks.Redis.from_url")
def test_check_readiness_reports_available_dependencies(
    redis_from_url,
    database_cursor,
):
    redis_from_url.return_value.ping.return_value = True

    assert check_readiness() == {"database": True, "redis": True}


@patch("apps.health.checks.connection.cursor", side_effect=RuntimeError("db secret"))
@patch("apps.health.checks.Redis.from_url")
def test_check_readiness_reports_database_failure_without_exception_details(
    redis_from_url,
    database_cursor,
):
    redis_from_url.return_value.ping.return_value = True

    assert check_readiness() == {"database": False, "redis": True}


@patch("apps.health.checks.connection.cursor")
@patch("apps.health.checks.Redis.from_url")
def test_check_readiness_reports_redis_failure_without_exception_details(
    redis_from_url,
    database_cursor,
):
    redis_from_url.return_value.ping.side_effect = RuntimeError("redis secret")

    assert check_readiness() == {"database": True, "redis": False}


@patch(
    "apps.health.views.check_readiness",
    return_value={"database": True, "redis": True},
)
def test_health_endpoint_returns_sanitized_success_response(readiness_check):
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {"database": "ok", "redis": "ok"},
    }


@patch(
    "apps.health.views.check_readiness",
    return_value={"database": False, "redis": True},
)
def test_health_endpoint_returns_sanitized_unavailable_response(readiness_check):
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "dependencies": {"database": "unavailable", "redis": "ok"},
    }
