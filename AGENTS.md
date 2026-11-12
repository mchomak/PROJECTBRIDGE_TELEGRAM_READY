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
# ProjectBridge: Stages 01-03 local runtime, accounts, projects, and passport

ProjectBridge is a React/Vite frontend and Django/DRF ASGI modular monolith. PostgreSQL is the source of truth; Redis backs Celery and Channels. Runtime pins: Python 3.13.18 / Django 5.2.19; Node 24.22.2 / React 19.3.1 / Vite 8.3.7 / React Router 7; PostgreSQL 17 with pgvector 0.8.7; Redis 7.4.12; Channels 4.3.2; Celery 5.7.0. Implemented slices are accounts and projects/passport. Stage 03 has no invitation, customer-acceptance, questionnaire, Project State, or progress workflow.

## Runtime and entry points

- `docker-compose.yml` runs `frontend`, `backend`, `db`, `redis`, and `celery-worker`. Vite is published on loopback port 5173; Django on `BACKEND_HOST_PORT` (default 8000). PostgreSQL and Redis are Compose-network services. PostgreSQL and media use named volumes; ordinary `docker compose down` preserves them. Do not use `down -v` for routine stops. Celery Beat is absent.
- Backend settings live in `backend/config/settings/`. `backend/config/urls.py` mounts health at `/api/v1/health/`, auth at `/api/v1/auth/`, projects at `/api/v1/projects/`, and development schema/docs at `/api/schema/` and `/api/docs/`. `backend/config/asgi.py` routes HTTP and WebSockets; the health probe is `/ws/v1/health/`. `backend/config/celery_app.py` configures Celery; `backend/apps/common/tasks.py` owns retry-safe `runtime_probe`.
- From the repo root, create `.env` only when absent, then start, migrate, inspect, and stop with:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose ps
docker compose down
```

Keep `.env` local; never read secrets into output or commit them. Backend and frontend source are baked into images without source bind mounts. After backend edits rebuild with `docker compose up --build -d backend` before live settings/schema/migration checks. After frontend edits rebuild/recreate with `docker compose up --build -d --no-deps frontend` before using the running frontend container.

## Backend ownership and public boundaries

- `backend/apps/accounts/` owns `accounts.User`, verification-token records, email normalization, registration, login, resend, and confirmation. `accounts/api/` exposes CSRF, register/login/logout/me, and email-verification endpoints. Browser auth uses Django's HttpOnly session cookie and CSRF on unsafe requests; local email uses Django's console backend (`docker compose logs -f backend`). Verification tokens are stored hashed; the email link token is read from the URL fragment.
- `backend/apps/projects/models.py` owns `Project`, `ProjectMember`, and `ProjectPassport`. Project types are `website`, `telegram_bot`, `automation`, `other`; statuses are `draft`, `active`, `completed`, `archived`; membership roles are `executor`, `customer`, and states are `active`, `left`, `revoked`. DB constraints enforce one row per project/user and at most one active member per role. Stage 03 creation adds only the creator as active executor; no endpoint creates or accepts a customer membership.
- Writes in `backend/apps/projects/services.py`: `create_project`, `update_project_metadata`, `complete_project`, `reopen_project`, `archive_project`, `restore_project`, `update_passport`. Reads in `backend/apps/projects/selectors.py`: `get_projects_for_member`, `get_project_for_member`, `get_active_project_members`, `get_passport_for_member`. `backend/apps/projects/api/` views authenticate/validate/orchestrate and map domain errors; keep business transitions in services.
- `backend/apps/common/models.py` owns `ProjectAuditLog`; `backend/apps/common/services.py::record_project_action` validates and persists safe metadata. Project writes and their audit rows share a transaction. Audit metadata records field names, status transitions, and passport versions, not project field values.
- Project endpoints: `GET, POST /api/v1/projects/`; `GET, PATCH /api/v1/projects/{project_id}/`; `GET /api/v1/projects/{project_id}/members/`; `POST /api/v1/projects/{project_id}/complete/`, `/reopen/`, `/archive/`, and `/restore/`; `GET, PATCH /api/v1/projects/{project_id}/passport/`. Endpoints require an authenticated session and CSRF for unsafe methods. Creation additionally requires verified email. Project, member, and passport reads are scoped to active membership; inaccessible project reads return 404. Member listing includes active memberships only.
- Project list defaults to non-archived projects; `status=archived` selects the archive. Ordering is `updated_at DESC, id ASC`, page size defaults to 20 and is capped at 100. Metadata accepts only `name`, `project_type`, `description`, requires an active executor membership, and is allowed only in `draft` or `active`. Lifecycle actions are executor-only: complete `active`; reopen `completed`; archive `draft`, `active`, or `completed` while saving prior status; restore to that status. Invalid transitions return 409. Project responses omit internal `status_before_archive`.
- Preserve migrations and local data: accounts `0001_initial`; projects `0001_initial`, `0002_project_constraints`; common `0001_enable_pgvector`, `0002_project_audit_log`.

## Passport schema and frontend contract

- A passport is created with each project at version 1. Read fields: `id`, `project_id`, `goal`, `target_audience`, `expected_result`, `functional_scope`, `integrations`, `constraints`, `deadline`, `budget_min`, `budget_max`, `currency`, `additional_data`, `version`, `created_at`, `updated_at`. Text fields default to empty strings; JSON fields to `{}`; date, decimal budgets, and currency are nullable. Budgets currently use `max_digits=30`, `decimal_places=10` in code (Stage 03 interfaces record this as an implementation assumption). Currency is nullable, limited to three ASCII letters, and uppercased.
- PATCH requires a positive integer `version` and at least one editable field from `goal`, `target_audience`, `expected_result`, `functional_scope`, `integrations`, `constraints`, `deadline`, `budget_min`, `budget_max`, `currency`, `additional_data`. Unknown fields are rejected. The service compares version atomically and increments once on success. A stale version returns 409 without passport mutation or audit row. Writes require executor membership and status `draft` or `active`; active members can read in every status.
- Frontend project data is owned by `frontend/src/entities/project/` (API, generated-schema types, query keys/hooks); mutations are in `frontend/src/features/projects/`. Public exports include `getProjects`, `getProject`, `getProjectMembers`, `getProjectPassport`, `useProjectList`, `useProject`, `useProjectMembers`, `useProjectPassport`, `useCreateProject`, `useUpdateProject`, `useProjectLifecycleAction`, and `useUpdatePassport`. API functions return `Promise<ProjectPage>`, `Promise<Project>`, `Promise<ProjectMember[]>`, and `Promise<ProjectPassport>` respectively; mutations use generated OpenAPI request/response types. Passport updates accept generated `ProjectPassportPatchSchema` with required `version`.
- `frontend/src/shared/api/index.ts` owns same-origin `apiJson`, session credentials, CSRF bootstrap/header, and `ApiError`; never store credentials in browser storage. Query hooks do not retry 4xx `ApiError`s and retry other failures up to two times. `frontend/src/app/App.tsx` redirects `/app` to `/app/projects`; child routes are projects, archive, new, and `:projectId`. Auth pages live under `frontend/src/pages/auth/`, project pages under `frontend/src/pages/projects/`, and the authenticated shell under `frontend/src/widgets/workspace-shell/`. FSD direction is `app -> pages -> widgets -> features -> entities -> shared`.

## Local checks and generated API types

Run from the repo root with the existing Compose images:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend python manage.py makemigrations --check --dry-run
docker compose run --rm --no-deps backend python manage.py spectacular --validate --file /tmp/openapi.yml
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose run --build --rm --no-deps frontend npm test
docker compose exec frontend npm run build
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
docker compose cp frontend:/app/src/shared/api/generated/schema.d.ts frontend/src/shared/api/generated/schema.d.ts
```

Frontend source is baked into the image. `frontend/scripts/generate-api-types.mjs` fetches OpenAPI from `API_SCHEMA_URL` and writes `/app/src/shared/api/generated/schema.d.ts` in the container; copy it to `frontend/src/shared/api/generated/schema.d.ts` after generation. Never edit generated types by hand.

Known verified Stage 03 results: backend suite 91 passed; frontend suite 29 passed; Ruff format/lint, migration check, drf-spectacular validation, frontend format/lint/typecheck/build, and API type generation passed. Do not report checks as passed unless run for the current change.
<!-- autopilot:end -->