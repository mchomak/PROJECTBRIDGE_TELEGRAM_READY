СДЕЛАНО:
- Backend pins, Django settings, package skeleton, ASGI, readiness, docs, WebSocket, Celery probe, and pgvector migration are implemented.
- Readiness (5), WebSocket (1), Celery (1), and schema/docs (1) focused tests pass in the pinned Python 3.13.18 container.
ФАЙЛЫ:
- Backend implementation and tests are under `backend/`.
- This handoff records the remaining ticket work.
РЕШЕНИЯ:
- `django_debug_mode = true` keeps pytest's test settings from removing development schema routes; production still gates docs on DEBUG=False.
- Schema test explicitly requests `application/vnd.oai.openapi+json`; the docs route needs Django's app-directory template loader.
ТУПИКИ:
- WebSocketCommunicator `wait()` returns task result, so verify clean close via `receive_output()`; test channel layer uses in-memory Redis substitute.
- Pytest-django defaults DEBUG off and lazy URL import dropped dev routes; confirmed with import-order reproductions before setting the explicit test option.
ДАЛЬШЕ:
- Add production secret/hosts/docs-disabled tests and pgvector migration behavior coverage; inspect tests for public behavior.
- From `backend/`, run the pinned container checks: `python -m pytest`, `ruff format --check .`, and `ruff check .`; fix failures within ticket 01.
