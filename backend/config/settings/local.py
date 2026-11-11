import os

from .base import *  # noqa: F403
from .base import LOCAL_SECRET_KEY, parse_csv_environment

DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or LOCAL_SECRET_KEY
ALLOWED_HOSTS = parse_csv_environment("DJANGO_ALLOWED_HOSTS") or [
    "localhost",
    "127.0.0.1",
    "backend",
    "testserver",
]
CSRF_TRUSTED_ORIGINS = parse_csv_environment("DJANGO_CSRF_TRUSTED_ORIGINS")
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
FRONTEND_BASE_URL = (
    os.environ.get("FRONTEND_BASE_URL") or "http://localhost:5173"
).rstrip("/")
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
