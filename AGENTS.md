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
# ProjectBridge: Stages 01 and 02: Local Runtime and Accounts

ProjectBridge is a React/Vite frontend and Django/DRF ASGI modular monolith, with PostgreSQL as source of truth, pgvector, Redis for Celery and Channels, and Docker Compose. Runtime pins: Python 3.13.18 / Django 5.2.19; Node 24.22.2 / React 19.3.1 / Vite 8.3.7; PostgreSQL 17 with pgvector 0.8.7; Redis 7.4.12; Channels 4.3.2; Celery 5.7.0. The current product slice is accounts/auth only; do not add memberships, invitations, password reset, MFA, SSO, or account deletion.

## Runtime and entry points

- `docker-compose.yml` runs `frontend`, `backend`, `db`, `redis`, and `celery-worker`. PostgreSQL data and uploaded media use named volumes; `docker compose down` preserves them, so do not add `-v`. The backend listens inside Compose on port 8000; direct host requests use `BACKEND_HOST_PORT`. Redis and PostgreSQL are Compose-network services. Celery Beat is absent.
- Backend settings are in `backend/config/settings/`. `backend/config/urls.py` registers readiness at `/api/v1/health/`, authentication under `/api/v1/auth/`, and development-only schema/docs at `/api/schema/` and `/api/docs/`. Readiness in `backend/apps/health/checks.py` checks PostgreSQL and Redis.
- `backend/config/asgi.py` routes HTTP and WebSocket traffic. The Channels probe `/ws/v1/health/` is registered in `backend/apps/health/routing.py` and handled in `backend/apps/health/consumers.py`. `backend/config/celery_app.py` configures the worker. `backend/apps/common/migrations/0001_enable_pgvector.py` enables pgvector; `backend/apps/common/tasks.py` owns the retry-safe `runtime_probe` task.
- PostgreSQL is the source of truth; Redis backs Celery and the Channels layer. Compose publishes Vite on loopback port 5173 and Django through `BACKEND_HOST_PORT`.
- Frontend FSD dependency flow is `app -> pages -> widgets -> features -> entities -> shared`. `frontend/src/app/App.tsx` owns startup/routes; auth routes are composed in `frontend/src/pages/auth/`; actions are in `frontend/src/features/auth/model/authActions.ts`; current-user state is in `frontend/src/entities/user/model/currentUser.ts`; `frontend/src/shared/api/index.ts` owns same-origin requests and CSRF. `frontend/scripts/generate-api-types.mjs` generates `frontend/src/shared/api/generated/schema.d.ts` from OpenAPI; do not edit generated types by hand.

## Accounts, sessions, and verification

- `backend/apps/accounts/models.py` owns `accounts.User` and verification-token records; `backend/apps/accounts/services.py` owns email normalization, registration, authentication, resend, and confirmation. `backend/apps/accounts/api/urls.py` exposes `GET /api/v1/auth/csrf/`, `POST /api/v1/auth/register/`, `POST /api/v1/auth/login/`, `POST /api/v1/auth/logout/`, `POST /api/v1/auth/email-verification/resend/`, `POST /api/v1/auth/email-verification/confirm/`, and `GET /api/v1/auth/me/`. API views orchestrate requests and sessions; business transitions remain in services. `backend/apps/common/api/errors.py` provides the shared error envelope with `code`, `detail`, `errors`, and `request_id`.
- Browser auth uses Django's HttpOnly session cookie and CSRF on all state-changing requests, including registration/login. The shared client obtains the token from the CSRF cookie or `GET /api/v1/auth/csrf/`, then sends `X-CSRFToken`. Do not store session credentials in browser storage.
- Login may create a session before email verification. `/app` loads `/api/v1/auth/me/`; a `401` redirects to `/login`, unverified users go to `/verification-required`, and network/server errors stay retryable. Verification tokens are stored as hashes; registration/resend sends the email after commit and resend responses do not disclose account existence. The local email backend is Django's console backend; check `docker compose logs -f backend`. The verification link token is in the URL fragment, which `frontend/src/pages/auth/ui/VerifyEmailPage.tsx` removes before submitting it.
- `backend/apps/accounts/migrations/0001_initial.py` adds the custom user model. Preserve existing migrations, the `auth_user` table, and local data; do not reset the database or Compose volumes.

## Local workflow and environment

See [docs/operations/LOCAL_DEVELOPMENT.md](docs/operations/LOCAL_DEVELOPMENT.md). From the repository root, copy `.env.example` only if `.env` is absent, then start, migrate, inspect, and stop:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose ps
docker compose down
```

`.env.example` variable names: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`, `BACKEND_HOST_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `REDIS_PASSWORD`. Compose wiring also uses `DJANGO_SETTINGS_MODULE`, `DB_HOST`, `DB_PORT`, `REDIS_URL`, `API_PROXY_TARGET`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. `FRONTEND_BASE_URL` is required in production. Keep `.env` local and never copy secret values into docs or commits.

Backend source is baked into the image without a source bind mount. After backend edits, rebuild/recreate it with `docker compose up --build -d backend` before checking live settings or migrations. Ordinary `docker compose down` preserves named volumes; never use `-v` for routine stops.

## Verified checks

Run from the repository root with the Compose images:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend python manage.py makemigrations --check --dry-run
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
docker compose exec frontend npm run build
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
```

Verified results: backend suite 51 passed; frontend suite 19 passed; Ruff formatting/lint, migration check, frontend format/lint/typecheck/build, and live API type generation passed. Runtime probes returned HTTP 200 for health/schema/docs and the Vite health proxy; PostgreSQL reported `vector`, Celery `runtime_probe` returned `{'status': 'ok'}`, the WebSocket probe returned `{'status': 'ok'}` and closed with code 1000, and DB/media markers survived an ordinary restart.
<!-- autopilot:end -->