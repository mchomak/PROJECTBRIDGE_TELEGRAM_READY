# 03 — Compose runtime and clean setup guide

**Requirements:** R21-R22, R24, R26-R29, R33-R35, R38-R54
**Blocked by:** 01, 02
**Zone:** `docker-compose.yml`, `infra/`, `.env.example`, `README.md`, `docs/operations/LOCAL_DEVELOPMENT.md`
**Wave:** 3
**Status:** done

## What must work

Compose builds and starts the backend and frontend along with PostgreSQL/pgvector, Redis, and the Celery worker. The setup guide explains a clean local start and provides commands that verify browser delivery, health, database extension, API and WebSocket proxies, Celery task delivery, and persistence.

## From the brief, verbatim

> “Add Docker Compose services for frontend, backend, PostgreSQL with pgvector, Redis, and Celery worker.”
> “Add health checks and persistent named volumes for database and uploaded-file storage.”
> “Document commands to start, stop, inspect logs, run migrations, and execute tests.”
> “Verify the complete local runtime from a clean setup and include exact startup, health-check, and test commands in the report.”

## Specification sections

Local runtime; Operational failure behavior; Local setup commands; Version and compatibility decisions; Celery Beat exclusion; Out of scope.

## Acceptance criteria

- [ ] Compose defines the named frontend, backend, db, redis, and celery-worker services with fixed compatible images, health checks, and healthy dependency ordering; no Beat service exists.
- [ ] Backend and frontend images build from committed lock files and run the app commands; `.env.example` contains safe placeholders and matches the documented environment contract.
- [ ] Database and uploaded-media storage use named volumes; normal `docker compose down` and subsequent `up` retain seeded data.
- [ ] Local Django email output is visible through the console backend; no secrets are logged or checked into `.env.example`.
- [ ] `LOCAL_DEVELOPMENT.md` gives equivalent PowerShell/POSIX setup, startup, status/log, migration, tests, health, pgvector, Celery probe, API docs/type generation, and stop commands.
- [ ] `npm run api:types` succeeds against the live Compose schema endpoint (`http://backend:8000/api/schema/`) and writes a non-empty generated TypeScript declaration; the guide documents the exact command/environment setting.
- [ ] A fresh `docker compose up --build -d` succeeds; all expected services become healthy; the frontend responds on 5173 and backend health on 8000.
- [ ] The documented runtime probe confirms `/api/v1/health/`, `/ws/v1/health/`, `/api/schema/`, `/api/docs/`, and both Vite proxies. In particular, a WebSocket connection through Vite to `ws://localhost:5173/ws/v1/health/` receives `{"status":"ok"}` and closes normally; pgvector is available in the configured database; and a Celery task result is received by the real worker.
- [ ] The guide documents that Beat is deferred until a scheduled task enters scope and that the stage adds no product behavior.
- [ ] Ordinary restart persistence is demonstrated without deleting volumes. Report exact executed commands and outcomes; run backend and frontend checks from their instructions.
