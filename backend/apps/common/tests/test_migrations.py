import pytest
from django.db import connection


@pytest.mark.django_db
def test_initial_migration_enables_pgvector_extension():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT extname FROM pg_extension WHERE extname = %s", ["vector"]
        )
        extension = cursor.fetchone()

    assert extension == ("vector",)
