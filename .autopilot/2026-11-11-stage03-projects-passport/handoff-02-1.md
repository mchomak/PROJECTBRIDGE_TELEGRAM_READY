СДЕЛАНО: List, create, detail, member list, metadata PATCH реализованы.
Покрыты verified creation, четыре project types, enum/name/unknown-field validation.
Membership scope, archive list, pagination bounds, role/state rules и audit проверены.
ФАЙЛЫ: backend/apps/projects/api/views.py, serializers.py, urls.py.
Готовы backend/apps/projects/selectors.py и расширение services.py.
Тесты находятся в backend/apps/projects/tests/test_api.py.
РЕШЕНИЯ: page size по умолчанию 20; page_size ограничен 100.
Порядок списка: updated_at DESC, id ASC; обычный список исключает archived.
Member summary id — UUID пользователя; email не выдаётся.
Metadata write и audit field names выполняются атомарно в projects.services.
Audit metadata содержит только sorted changed_fields, без значений.
ТУПИКИ: после добавления list view оставался старый get() с Response([]); удалён.
Pagination fixture должен задавать одинаковый updated_at, чтобы проверить tie-break по id.
ДАЛЬШЕ: после rebuild запустить ruff format/check и makemigrations --check.
Затем проверить OpenAPI schema, focused test_api и полный backend pytest; не коммитить.
