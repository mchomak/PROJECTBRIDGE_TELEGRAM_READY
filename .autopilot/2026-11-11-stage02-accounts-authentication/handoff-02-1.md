СДЕЛАНО: csrf, register, login, logout и me endpoints реализованы с OpenAPI схемами.
СДЕЛАНО: Регистрация, session login, единый 401, профиль, 204 logout и CSRF проверены.
СДЕЛАНО: Тест `test_auth.py` прошёл: 11 passed; документация и полные проверки не выполнены.
ФАЙЛЫ: `backend/apps/accounts/api/core/` и `backend/apps/accounts/api/core_urls.py` готовы.
ФАЙЛЫ: `backend/apps/accounts/tests/api/test_auth.py` готов, focused suite зелёный.
ФАЙЛЫ: `docs/api/`, `docs/security/`, `docs/OPEN_DECISIONS.md` ещё не обновлялись.
РЕШЕНИЯ: Анонимные POST проверяются через SessionAuthentication.enforce_csrf; CSRF ошибка скрывает middleware reason.
РЕШЕНИЯ: Собственное 401 исключение сохраняет контракт, поскольку DRF SessionAuthentication обычно отвечает 403.
РЕШЕНИЯ: Login до подтверждения email разрешён; rate scopes уже заданы в ticket 01 settings.
ТУПИКИ: Backend код запечён в образ; пересобирай `docker compose build backend` перед pytest.
ТУПИКИ: Rate-limit cache общий между тестами; в test_auth.py добавлен autouse cache clear.
ТУПИКИ: Weak-password Django ValidationError приходит списком; API отображает его в errors.password.
ДАЛЬШЕ: Обновить API_CONTRACT.md и ACCESS_CONTROL_AND_SECURITY.md и только item 21 OPEN_DECISIONS.md.
ДАЛЬШЕ: Исправить возможные ruff format/check ошибки и выполнить полный backend suite.
ДАЛЬШЕ: Проверить OpenAPI schema/live endpoint; затем вернуть DONE или точный оставшийся blocker.
