import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

LOCAL_SECRET_KEY = "projectbridge-local-insecure-secret-for-development-only"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_production_process(
    script: str,
    *,
    secret_key: str | None,
    allowed_hosts: str | None,
) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
    environment.pop("DJANGO_SECRET_KEY", None)
    environment.pop("DJANGO_ALLOWED_HOSTS", None)
    environment.pop("DJANGO_CSRF_TRUSTED_ORIGINS", None)
    environment["FRONTEND_BASE_URL"] = "https://app.example"

    if secret_key is not None:
        environment["DJANGO_SECRET_KEY"] = secret_key
    if allowed_hosts is not None:
        environment["DJANGO_ALLOWED_HOSTS"] = allowed_hosts

    return subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        cwd=BACKEND_DIR,
        env=environment,
        text=True,
    )


@pytest.mark.parametrize(
    ("secret_key", "allowed_hosts", "expected_error"),
    [
        (
            None,
            "api.example.com",
            "Production requires an explicit non-local DJANGO_SECRET_KEY.",
        ),
        (
            LOCAL_SECRET_KEY,
            "api.example.com",
            "Production requires an explicit non-local DJANGO_SECRET_KEY.",
        ),
        (
            "production-secret-key-for-isolated-settings-test",
            None,
            "Production requires DJANGO_ALLOWED_HOSTS.",
        ),
    ],
    ids=["missing-secret", "local-secret", "missing-hosts"],
)
def test_production_rejects_unsafe_secret_or_host_configuration(
    secret_key,
    allowed_hosts,
    expected_error,
):
    result = run_production_process(
        "from django.conf import settings\nsettings.SECRET_KEY",
        secret_key=secret_key,
        allowed_hosts=allowed_hosts,
    )

    assert result.returncode != 0
    assert expected_error in result.stderr


def test_production_disables_debug_and_development_documentation_routes():
    script = """
import json

import django
django.setup()

from django.conf import settings
from django.test import Client

client = Client()
schema_status = client.get("/api/schema/", HTTP_HOST="api.example.com").status_code
docs_status = client.get("/api/docs/", HTTP_HOST="api.example.com").status_code
print(json.dumps({
    "debug": settings.DEBUG,
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "schema_status": schema_status,
    "docs_status": docs_status,
}))
"""
    result = run_production_process(
        script,
        secret_key="production-secret-key-for-isolated-settings-test",
        allowed_hosts=" api.example.com, admin.example.com ",
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "debug": False,
        "allowed_hosts": ["api.example.com", "admin.example.com"],
        "schema_status": 404,
        "docs_status": 404,
    }


def test_production_uses_secure_browser_cookie_defaults():
    script = (
        "import json\n"
        "import django; django.setup()\n"
        "from django.conf import settings\n"
        "print(json.dumps({"
        "'session_httponly': settings.SESSION_COOKIE_HTTPONLY, "
        "'session_secure': settings.SESSION_COOKIE_SECURE, "
        "'session_samesite': settings.SESSION_COOKIE_SAMESITE, "
        "'csrf_httponly': settings.CSRF_COOKIE_HTTPONLY, "
        "'csrf_secure': settings.CSRF_COOKIE_SECURE, "
        "'csrf_samesite': settings.CSRF_COOKIE_SAMESITE}))"
    )
    result = run_production_process(
        script,
        secret_key="production-secret-key-for-isolated-settings-test",
        allowed_hosts="api.example.com",
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "session_httponly": True,
        "session_secure": True,
        "session_samesite": "Lax",
        "csrf_httponly": False,
        "csrf_secure": True,
        "csrf_samesite": "Lax",
    }
