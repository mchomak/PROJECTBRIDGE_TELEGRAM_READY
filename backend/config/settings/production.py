from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import LOCAL_SECRET_KEY, parse_csv_environment
from .base import SECRET_KEY as BASE_SECRET_KEY

DEBUG = False
SECRET_KEY = BASE_SECRET_KEY.strip()
ALLOWED_HOSTS = parse_csv_environment("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = parse_csv_environment("DJANGO_CSRF_TRUSTED_ORIGINS")

if not SECRET_KEY or SECRET_KEY == LOCAL_SECRET_KEY:
    raise ImproperlyConfigured(
        "Production requires an explicit non-local DJANGO_SECRET_KEY."
    )
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production requires DJANGO_ALLOWED_HOSTS.")
