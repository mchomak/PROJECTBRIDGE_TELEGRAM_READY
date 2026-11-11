# Stage 01 — Application Skeleton and Local Runtime

**Goal:** Make the empty frontend and backend run together locally using
the agreed infrastructure.

## Read first

- `AGENTS.md`
- `docs/architecture/SYSTEM_ARCHITECTURE.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`
- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/operations/LOCAL_DEVELOPMENT.md`
- `docs/api/API_CONTRACT.md`

## Dependencies

Stage 00.

## Scope

### Backend skeleton

- Initialize Django and Django REST Framework.
- Configure ASGI as the application entry point.
- Add the planned Django app package structure without speculative
  business models.
- Configure Django Channels.
- Configure Celery and Redis broker integration.
- Add a minimal health endpoint.
- Configure drf-spectacular and expose the OpenAPI schema and Swagger UI
  in development.
- Establish settings separation for local development and
  production-safe defaults.
- Configure PostgreSQL and the pgvector extension availability.

### Frontend skeleton

- Initialize React, TypeScript, and Vite.
- Create the FSD layer directories: `app`, `pages`, `widgets`,
  `features`, `entities`, `shared`.
- Add application routing and a minimal application shell.
- Create a shared API client boundary.
- Configure Vite proxying for `/api/` and `/ws/`.
- Establish a reproducible OpenAPI-to-TypeScript type generation
  command. Do not hand-write duplicate API types.

### Local runtime

- Add Docker Compose services for frontend, backend, PostgreSQL with
  pgvector, Redis, and Celery worker.
- Add Celery Beat only if a scheduled task is already required by the
  implemented scope; otherwise leave it documented for later.
- Add health checks and persistent named volumes for database and
  uploaded-file storage.
- Configure Django console email for local development.
- Document commands to start, stop, inspect logs, run migrations, and
  execute tests.

## Out of scope

- User registration and business models.
- Product screens beyond the minimal shell.
- Project workflows or AI provider integrations.

## Deliverables

- Running Django ASGI application.
- Running React/Vite application.
- Working PostgreSQL and Redis services.
- Working Celery worker connection.
- Working Channels ASGI configuration.
- OpenAPI schema and interactive docs.
- Generated TypeScript type workflow.
- Docker Compose and local setup documentation.

## Acceptance criteria

- [ ] A clean local setup can start all required services using
  documented commands.
- [ ] Frontend loads in the browser.
- [ ] Backend health endpoint returns success.
- [ ] Backend connects to PostgreSQL and Redis.
- [ ] pgvector is available in the configured database.
- [ ] Celery worker starts and receives a test task.
- [ ] ASGI application starts with HTTP and WebSocket routing
  configured.
- [ ] `/api/schema/` and `/api/docs/` are available in development.
- [ ] Vite proxies `/api/` and `/ws/` correctly.
- [ ] Database data survives ordinary container restarts.
- [ ] No domain functionality is implemented prematurely.

## Stop conditions

Do not guess incompatible package versions or database images. If a
version decision affects pgvector, Django, Channels, or Celery
compatibility, verify compatibility and document the chosen versions.

## Codex handoff

Implement Stage 01 only. Verify the complete local runtime from a clean
setup and include exact startup, health-check, and test commands in the
report.
