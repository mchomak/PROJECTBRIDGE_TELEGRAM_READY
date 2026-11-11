# Stage 01 implementation boundaries

## Resolved in the specification

ProjectBridge is a React, TypeScript, Vite frontend and a Python, Django, DRF backend in one repository. Django remains a modular monolith. REST is for resource operations and WebSocket is for real-time delivery; PostgreSQL is the source of truth. Stage 01 has no product features, business models, user registration, or speculative abstractions.

### Backend boundary

- `config` owns settings selection, URL registration, ASGI composition, and Celery bootstrap.
- `apps.common` owns the pgvector extension migration and generic operational probe integration. It exposes no domain model or cross-app business service.
- `apps.health` owns readiness checks and the read-only health response. It reports PostgreSQL and Redis availability without internal connection details.
- The planned Django packages are `accounts`, `projects`, `invitations`, `questionnaire`, `chat`, `documents`, `project_state`, `ai_assistant`, `specifications`, `common`, and `health`. Add package initializers and app configurations; add no speculative models, services, selectors, serializers, or business endpoints.
- `config.asgi.application` is the entry point. HTTP and the `/ws/v1/` WebSocket router share Daphne and a Redis-backed Channels layer. `/api/v1/health/` and `/ws/v1/health/` are operational probes only. Development schema/docs are `/api/schema/` and `/api/docs/`.
- Celery uses Redis as broker and result backend. The runtime probe task is safe to repeat and carries no product behavior. Do not add Beat.
- Local, test, and production settings are separate. Production has `DEBUG=False`, requires a non-local explicit secret and allowed hosts, and does not inherit local secrets. Local email is console output.
- The sole migration is the pgvector extension migration, owned by `apps.common`.

### Frontend boundary

- `app` owns initialization, route composition, global providers, and the root shell.
- `shared/api` owns the single fetch boundary and generated OpenAPI declaration. It exposes a request function and generated paths while hiding cookie parsing and request defaults.
- `frontend/src` has `app`, `pages`, `widgets`, `features`, `entities`, and `shared` layers. Stage 01 adds no product query or workflow.
- Vite proxies `/api/` and `/ws/` to the backend and supports WebSocket upgrades. Unknown routes render a short not-found state.
- `api:types` generates the API declaration from the running schema endpoint. Generated output is never edited manually.

### Runtime boundary

- Compose services are named `frontend`, `backend`, `db`, `redis`, and `celery-worker`.
- Compose exposes frontend port 5173 and backend port 8000. PostgreSQL and Redis are internal services used via Compose; their credentials are supplied through `.env` and are not published in application output.
- Backend environment names are `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `REDIS_URL`. Compose uses service hostnames `db` and `redis`.
- PostgreSQL uses `pgvector/pgvector:0.8.7-pg17-bookworm`; Redis uses `redis:7.4.12-alpine3.21`; Python uses `python:3.13.18-slim-bookworm`; Node uses `node:24.22.2-alpine3.23`.
- PostgreSQL data and uploaded media use named volumes. `docker compose down` preserves them; do not use `down -v` in acceptance verification.
- Python dependency and tool declarations/locks live in `backend/requirements.txt` and `backend/pyproject.toml`, following the documented backend working directory.
- Health checks report service readiness. Compose waits for Postgres and Redis before backend startup. No destructive recovery is automatic.
- Local complete-runtime verification uses `docker compose up --build -d`, checks service status and HTTP/WebSocket/API proxy routes, submits and fetches a Celery probe result, checks `pg_extension`, and confirms persistence after ordinary restart.

## Exact versions

Python 3.13.18; Django 5.2.19; djangorestframework 3.17.2; drf-spectacular 0.30.0; Channels 4.3.2; Daphne 4.2.1; channels_redis 4.3.0; Celery 5.7.0; redis-py 6.4.0; pgvector 0.5.1; psycopg[binary] 3.3.8; pytest 9.2.0; pytest-django 4.14.0; Ruff 0.17.4. PostgreSQL/pgvector image is `pgvector/pgvector:0.8.7-pg17-bookworm`; Redis server image is `redis:7.4.12-alpine3.21`.

Node 24.22.2; React/React DOM 19.3.1; @types/react 19.3.0; @types/react-dom 19.3.0; @types/node 24.19.2; TanStack Query 5.107.1; TypeScript 5.9.3; Vite 8.3.7; @vitejs/plugin-react 6.3.0; react-router 7.16.0; openapi-typescript 7.13.0; Biome 2.6.6; Vitest 4.1.12; React Testing Library 16.3.3; jsdom 31.0.0. Pin direct dependencies and commit lock files.

## Run and check commands

- From repository root: `docker compose up --build -d`, `docker compose ps`, `docker compose logs -f`, `docker compose down`.
- Migrations: `docker compose exec backend python manage.py migrate`.
- Backend install and checks, from `backend/`: `python -m pip install -r requirements.txt`, then `ruff format --check .`, `ruff check .`, `python -m pytest`.
- Frontend checks, from `frontend/`: `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm test`.
- OpenAPI types are generated with `docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types`; verify that this writes a non-empty declaration from the live backend schema.

## Missing prerequisites

The host may not have the pinned runtimes or project dependencies preinstalled. Use the exact pinned official container image (Python `python:3.13.18-slim-bookworm`, Node `node:24.22.2-alpine3.23`) or a disposable virtual environment, and install only the exact project pins there for checks. Do not install into the global host environment or substitute versions. Return `BLOCKED` only if the exact image or a required exact dependency cannot actually be fetched/used, with the command and error as evidence. Do not silently change these interfaces. Do not touch files outside the assigned ticket zone unless a required shared interface fails; report that as `BLOCKED` first.

## From ticket 01 — provisional implementation

- `config.asgi.application` composes the Django HTTP app and WebSocket health route; `config.celery_app.app` is the Celery entry point.
- `GET /api/v1/health/` checks PostgreSQL and Redis; `/ws/v1/health/` returns a status and closes.
- `runtime_probe() -> {"status": "ok"}` is the Celery task used to prove worker delivery.
- The pytest config explicitly enables development schema URLs for tests. Schema JSON requests use `Accept: application/vnd.oai.openapi+json`; production settings remain DEBUG off and docs disabled.
- Focused tests reported green: health/readiness (5), ASGI/WebSocket (1), Celery task (1), and schema/docs (1). Full checks and production/migration coverage remain open.

## Ticket 01 completion checkpoint

- Production settings require the configured non-local secret and allowed hosts; production docs are disabled.
- The pgvector extension migration passed against PostgreSQL 17 with the pinned pgvector image, and the catalog test confirmed the vector extension.
- Ticket 01 returned full pytest: 13 passed; Ruff format check and lint both passed in the pinned Python 3.13.18 container. The coordinator repeats the full suite before review completes.

## Ticket 02 completion checkpoint

- Frontend uses the pinned Node 24.22.2 container and `npm ci`; coordinator checks passed for format both before and after build, lint, typecheck, 4 tests, and production build.
- The root route rendered through Vite with HTTP 200. `shared/api` provides the same-origin fetch boundary and CSRF support; Vite has `/api/` and WebSocket upgrade proxy configuration.
- `api:types` intentionally fails visibly if its configured schema endpoint is unavailable. Ticket 03 must verify successful generation against the live Compose backend and confirm both HTTP and WebSocket proxy delivery.

## Ticket 03 completion checkpoint

- Compose defines `frontend`, `backend`, `db`, `redis`, and `celery-worker`, with the backend and worker sharing the pinned Python image. PostgreSQL data and media use named volumes; Beat is absent.
- The full stack reached 5/5 healthy on the documented `BACKEND_HOST_PORT=8001` override because another active local project owns host port 8000; the clean-machine default remains 8000. The stack is left running.
- Runtime verification returned HTTP 200 for the frontend, backend health, Vite API proxy, schema, and docs; the Vite WebSocket proxy returned `{"status":"ok"}` and close code 1000. pgvector was present, the local email backend was console, a non-eager Celery task returned `{"status":"ok"}`, and live OpenAPI generation wrote a 4,221-byte declaration.
- Database and media markers survived ordinary `docker compose down` followed by `docker compose up --build -d`; no volumes were deleted.
- Backend suite: 13 passed using `DJANGO_SETTINGS_MODULE=config.settings.test`; frontend suite: 4 passed. Ruff format/lint, Biome format/lint, TypeScript check, and production build passed. POSIX command variants were documented but executed only from the available PowerShell host.

## Ticket 04 completion checkpoint

- The Compose frontend host port is bound to `127.0.0.1:5173`; it remains available at `http://localhost:5173/` and is not published on other host interfaces. The frontend container health check is unchanged. `docker compose config --quiet`, frontend health, and the host HTTP request passed; review found no blocking issues.
