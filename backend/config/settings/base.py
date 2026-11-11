import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_SECRET_KEY = "projectbridge-local-insecure-secret-for-development-only"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS = []
CSRF_TRUSTED_ORIGINS = []

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "apps.accounts.apps.AccountsConfig",
    "apps.projects.apps.ProjectsConfig",
    "apps.invitations.apps.InvitationsConfig",
    "apps.questionnaire.apps.QuestionnaireConfig",
    "apps.chat.apps.ChatConfig",
    "apps.documents.apps.DocumentsConfig",
    "apps.project_state.apps.ProjectStateConfig",
    "apps.ai_assistant.apps.AiAssistantConfig",
    "apps.specifications.apps.SpecificationsConfig",
    "apps.common.apps.CommonConfig",
    "apps.health.apps.HealthConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {},
    }
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "projectbridge"),
        "USER": os.environ.get("DB_USER", "projectbridge"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "projectbridge-local"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
STATIC_URL = "static/"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "ProjectBridge API",
    "DESCRIPTION": "ProjectBridge operational API scaffold.",
    "VERSION": "1.0.0",
}


def parse_csv_environment(name: str) -> list[str]:
    return [
        value.strip() for value in os.environ.get(name, "").split(",") if value.strip()
    ]
