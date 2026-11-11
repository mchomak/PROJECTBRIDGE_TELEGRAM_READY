# AGENTS.md

Shared coding instructions for all agents working in ProjectBridge.

## 1. Project context

ProjectBridge is a collaborative project workspace. The MVP must run
locally with persistent data and working end-to-end workflows.

**Stack**

- Frontend: React, TypeScript, Vite, Feature-Sliced Design.
- Backend: Python, Django, Django REST Framework.
- Data/runtime: PostgreSQL + pgvector, Redis, Celery, Django
  Channels/WebSocket.
- Local orchestration: Docker Compose.
- API contract: OpenAPI via drf-spectacular; frontend types generated
  from OpenAPI.

**Architecture**

- One Git monorepo.
- Backend is a modular monolith, not microservices.
- Domain logic belongs to its owning Django app and service layer.
- Frontend dependencies follow FSD direction:
  `app -> pages -> widgets -> features -> entities -> shared`.
- REST handles resource operations; WebSocket delivers real-time chat
  events. PostgreSQL is the source of truth.

## 2. Source of truth

Before coding, read:

1.  `docs/README.md`
2.  Relevant technical documents under `docs/`.
3.  `docs/OPEN_DECISIONS.md`
4.  The current brief under `docs/implementation/stages/`.

The stage brief defines the current task scope. Technical documents
define system-wide contracts.

If documents conflict, a requirement is ambiguous, or an unresolved
decision blocks implementation: **stop and report the exact issue**. Do
not silently choose an interpretation or invent product behavior. The
project owner resolves it and updates the documentation.

When an accepted architecture decision changes, update the relevant
technical document and add or amend an ADR.

## 3. Product invariants

- Initial project types: `website`, `telegram_bot`, `automation`,
  `other`.
- Invitations are bound to a normalized email. Acceptance requires the
  user’s matching verified email.
- Project roles are `executor` and `customer`, scoped to each project.
- Customer can read all shared Project State but cannot directly modify
  structured entities.
- Customer cannot access internal AI analyses or pending AI proposals.
- Both participants can read and upload all project documents. Private
  documents do not exist.
- Document archiving and permanent deletion require both participants’
  consent. Follow the approved lifecycle; stop if product decisions and
  technical documents conflict.
- Maximum file size is 20 MB. MVP text extraction supports PDF, DOCX,
  TXT, and Markdown only. No OCR, audio, or video processing.
- Questionnaire schemas and branching are deterministic, versioned, and
  product-authored. AI must not generate questions or branching rules.
- Questionnaire answers are stored separately. Passport mapping must
  follow explicit rules; conflicts must never be silently overwritten.
- AI may detect contradictions and propose changes, but cannot decide
  which source is correct or mutate shared Project State without
  executor approval.
- Do not display project completion percentages.
- Public order import, formal specification approval, OCR, audio/video
  processing, and microservices are outside the MVP.

## 4. Think before coding

- State assumptions when they affect implementation.
- Surface trade-offs when multiple interpretations exist.
- Prefer the simplest solution that satisfies the task.
- Push back on unnecessary complexity.
- Ask before implementing behavior that depends on an unresolved product
  decision.

## 5. Scope and change discipline

- Implement only the current requested stage.
- Do not add future-stage functionality or speculative abstractions.
- Touch only files required by the task; do not refactor unrelated code
  or reformat unrelated files.
- Match existing repository conventions.
- Remove only unused code made obsolete by your own changes.
- Every change must trace directly to the current task.

## 6. Architecture rules

- Keep Django views thin. Put business operations in domain services.
- Use selectors/query functions for reads and services for state
  changes.
- Do not directly mutate another Django app’s models; use the owning
  app’s service interface.
- Avoid circular imports and cross-layer shortcuts.
- Do not put business rules in serializers, React components, or Celery
  task wrappers.
- Celery tasks call domain services, are retry-safe, and are enqueued
  after the database transaction commits.
- Frontend visibility is not authorization. Enforce every permission on
  the backend.
- Keep provider SDKs inside AI adapters. Never expose provider
  credentials to frontend code.
- Generate frontend API types from OpenAPI; do not edit generated types
  manually.

## 7. Implementation and verification loop

For each stage:

1.  Read the stage brief and referenced documents.
2.  Inspect the existing code before editing.
3.  State a short plan with verifiable outcomes.
4.  Implement the smallest complete vertical slice.
5.  Add tests for success, validation, permissions, and relevant failure
    paths.
6.  Run relevant tests, migrations, lint, type checks, and builds.
7.  Report changed files, exact checks/results, skipped checks, and
    unresolved blockers.

A stage is complete only after its acceptance criteria have been
verified. Never claim a test or command passed unless it was actually
run.

## 8. Verification and commits

- Prefer a regression test for every bug fix.
- Test role boundaries and cross-project isolation, not only happy
  paths.
- Verify migrations on a clean database.
- After API changes, regenerate/check OpenAPI and frontend types.
- Compute numeric or factual claims that can be checked; do not estimate
  acceptance-critical values.
- Keep one stage in one coherent, reviewable commit or a small set of
  directly related commits. Do not bundle unrelated stages.
- If a separate reviewer/tester is used, it is read-only and reports
  PASS/FAIL with precise findings.
- Do not mark a stage complete before verification passes.

## 9. Codex delegation

Use the stage brief as the full specification. Do not paste its entire
contents into a Codex prompt.

**Implementation prompt**

> Implement stage `<NN>` using
> `docs/implementation/stages/<stage-file>.md`. Read `AGENTS.md` and all
> referenced documents first. Inspect the repository, implement only
> this stage, run its acceptance checks, and report changed files, test
> results, and unresolved blockers. Stop if the documentation is
> ambiguous or conflicting.

**Review prompt**

> Review stage `<NN>` against its stage brief and referenced technical
> documents. Do not modify files. Return PASS or FAIL with precise
> findings and verification steps.

Do not spawn nested agents unless the project owner explicitly asks.

<!-- autopilot:start -->

# ProjectBridge: Stage 01: Application Skeleton and Local Runtime

ProjectBridge is a collaborative project workspace. Stage 01 provides a local React/Vite frontend, Django/DRF ASGI backend, PostgreSQL with pgvector, Redis, and a Celery worker. It intentionally contains no account flows, product workflows, business models, or AI integrations.

## Architecture and entry points

- The backend is a Django modular monolith. `backend/config/settings/` separates base, local, test, and production settings; `backend/config/urls.py` registers HTTP routes; `backend/config/asgi.py` composes HTTP and WebSocket routing; `backend/config/celery_app.py` configures Celery.
- `backend/apps/health/` owns readiness and the `/ws/v1/health/` probe. `backend/apps/common/` owns the pgvector migration and the retry-safe `runtime_probe` task. The only migration enables pgvector; domain app packages are empty shells.
- PostgreSQL is the source of truth. Redis backs Celery and Channels. Django serves `/api/v1/health/`, `/api/schema/`, and development `/api/docs/`; the Channels probe is `/ws/v1/health/`.
- The frontend follows FSD dependency direction: `app -> pages -> widgets -> features -> entities -> shared`. App startup/routes are in `frontend/src/app/`; the request boundary is `frontend/src/shared/api/`; `frontend/scripts/generate-api-types.mjs` generates OpenAPI declarations. Do not hand-edit generated API types.
- `docker-compose.yml` defines `frontend`, `backend`, `db`, `redis`, and `celery-worker`. Container definitions are in `infra/docker/`. PostgreSQL and uploaded media use named volumes. Vite's host port is loopback-bound at `127.0.0.1:5173`; Django's container port 8000 is published at `BACKEND_HOST_PORT`.
- Runtime pins include Python 3.13.18 / Django 5.2.19, Node 24.22.2 / Vite 8.3.7, PostgreSQL 17 with pgvector, and Redis 7.4.12. Dependency pins and lock files are committed. Celery Beat is absent because no scheduled task is in scope.

## Local workflow

See [docs/operations/LOCAL_DEVELOPMENT.md](docs/operations/LOCAL_DEVELOPMENT.md) for the full PowerShell and POSIX commands, runtime probes, and persistence check. From the repository root, copy `.env.example` only when `.env` does not already exist: PowerShell `if (-not (Test-Path .env)) { Copy-Item .env.example .env }`; POSIX `test -f .env || cp .env.example .env`. Then run:

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose exec backend python manage.py migrate
docker compose down
```

`docker compose down` preserves volumes; never add `-v` during ordinary stop or persistence checks. Backend HTTP is on host port 8000 by default. This workspace has another service on 8000, so its ignored local `.env` uses 8001; check the configured `BACKEND_HOST_PORT` before making direct backend requests. The clean-host default remains 8000.

## Verified checks

Run from the repository root with the pinned Compose images:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

The verified full suites passed: backend 13 tests, frontend 4 tests; formatting, lint, type-check, and production build passed. Compose builds install pinned dependencies from `backend/requirements.txt` and `frontend/package-lock.json` during `docker compose up --build -d`. Generate frontend types from the live backend schema with:

```sh
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
```

Backend health from PowerShell: `$backendHostPort = (Select-String -Path .env -Pattern '^BACKEND_HOST_PORT=').Line.Split('=')[1]`; then `Invoke-RestMethod "http://localhost:$backendHostPort/api/v1/health/"`. POSIX: `BACKEND_HOST_PORT="$(sed -n 's/^BACKEND_HOST_PORT=//p' .env | tr -d '\r')"`; then `curl --fail --show-error "http://localhost:${BACKEND_HOST_PORT}/api/v1/health/"`.

Use the runtime section of the operations guide for HTTP/schema/docs checks, the real Celery task command, pgvector query, Vite WebSocket probe, and the persistence restart procedure. Verified outcomes: health/schema/docs and Vite HTTP proxy returned 200; Celery returned `{'status':'ok'}`; PostgreSQL reported `vector`; WebSocket returned `{'status':'ok'}` and closed with code 1000; live type generation produced a 4,221-byte declaration; database and media markers survived an ordinary restart.

## Environment and gotchas

`.env.example` declares `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `BACKEND_HOST_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `REDIS_PASSWORD`. Compose also sets `DJANGO_SETTINGS_MODULE`, `DB_HOST`, `DB_PORT`, `REDIS_URL`, `API_PROXY_TARGET`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` for service wiring. Keep `.env` local and never copy secret values into docs or commits. Local email uses Django's console backend; inspect `docker compose logs -f backend`. For pytest, explicitly set `DJANGO_SETTINGS_MODULE=config.settings.test`. The POSIX port extraction in the operations guide removes carriage returns because a Windows-created `.env` may use CRLF.

<!-- autopilot:end -->