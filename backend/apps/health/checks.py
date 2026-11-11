from contextlib import suppress

from django.conf import settings
from django.db import connection
from redis import Redis


def check_readiness() -> dict[str, bool]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_available = True
    except Exception:
        database_available = False

    redis_client = None
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_available = bool(redis_client.ping())
    except Exception:
        redis_available = False
    finally:
        if redis_client is not None:
            with suppress(Exception):
                redis_client.close()

    return {"database": database_available, "redis": redis_available}
