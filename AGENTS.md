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

For frontend work, use the project-local skills in `.agents/skills/`:
`frontend-design` for design decisions, `web-design-guidelines` for UI
quality audits, and `webapp-testing` for Playwright browser verification.
Review their instructions and any scripts before use.

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
# ProjectBridge: local MVP through invitations, shared state, chat, and documents

ProjectBridge is a React/TypeScript/Vite frontend and Django/DRF ASGI modular monolith. PostgreSQL is the source of truth; Redis backs Celery, Channels, and throttling. Runtime pins: Python 3.13.18 / Django 5.2.19; Node 24.22.2 / React 19.3.1 / Vite 8.3.7 / React Router 7; PostgreSQL 17 with pgvector 0.8.7; Redis 7.4.12; Channels 4.3.2; Celery 5.7.0. Implemented workflows include accounts/projects/passport, verified-email invitations, deterministic questionnaires, shared Project State, persisted chat with WebSocket delivery, and shared documents with two-party lifecycle actions. AI analysis, document extraction, and specification workflows are not implemented.

## Runtime and entry points

- `docker-compose.yml` runs `frontend`, `backend`, `db`, `redis`, `celery-worker`, and `celery-beat`. Vite is published on loopback port 5173; Django on `BACKEND_HOST_PORT` (default 8000). PostgreSQL and Redis are Compose-network services. PostgreSQL and media use named volumes; ordinary `docker compose down` preserves them. Do not use `down -v` for routine stops.
- Local Compose inputs are named in `.env.example`: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`, `BACKEND_HOST_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `REDIS_PASSWORD`. Container settings also use `DB_HOST`, `DB_PORT`, and `REDIS_URL`. Keep `.env` local and never print or commit its values.
- Settings are in `backend/config/settings/`; `config/urls.py` mounts health, auth, invitation, questionnaire, Project State, project, and document APIs. `config/asgi.py` routes HTTP and authenticated WebSockets, including `/ws/v1/health/` and `/ws/v1/projects/{project_id}/chat/`. `config/celery_app.py` configures Celery; Beat runs the retry-safe document deletion sweep every 300 seconds and specification dispatch recovery every 60 seconds.
- From the repo root, start and migrate with:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose ps
```

Use `docker compose down` to stop services while preserving named volumes. Source is baked into images without source bind mounts: rebuild backend after backend edits with `docker compose up --build -d backend`; recreate frontend after frontend edits with `docker compose up --build -d --no-deps frontend` before inspecting the running app.

## Backend boundaries and APIs

- `backend/apps/accounts/` owns the user, normalized email, verification tokens, registration/login, and CSRF/session endpoints. Browser auth uses an HttpOnly session cookie and CSRF for unsafe requests. Local email uses Django's console backend; inspect it with `docker compose logs backend`.
- `backend/apps/projects/` owns `Project`, membership, passport, project lifecycle, and the public service boundary for invitation acceptance and versioned questionnaire mapping. Roles are `executor` and `customer`; reads are active-member scoped and writes enforce role/status rules in services. Passport writes are versioned and stale versions return 409.
- `backend/apps/invitations/` owns email-bound invitations and throttling. Create/list/revoke routes are under `/api/v1/projects/{project_id}/invitations/`; public preview/accept are under `/api/v1/invitations/`. Raw tokens are emailed and stored only as hashes; acceptance requires the matching verified normalized email.
- `backend/apps/questionnaire/` owns immutable product-authored JSON schemas in `schemas/`, submissions, answers, and its executor-only conflict queue. Project questionnaire APIs are under `/api/v1/projects/{project_id}/questionnaire/`; submission actions are under `/api/v1/questionnaire/`. Answers stay separate from the passport; explicit mapping calls the owning projects service and never silently overwrites conflicts.
- `backend/apps/project_state/` owns stages, requirements, tasks, open questions, conflicts, transitions, and evidence snapshots. Project State routes are under `/api/v1/projects/{project_id}/...`; the aggregate is `/state/`. Both roles can read shared state; structured changes are executor-only. Evidence resolvers read from the owning questionnaire/chat services. There is no completion-percentage field or display.
- `backend/apps/chat/` owns persisted messages, signed keyset cursors, idempotency, and rate limiting. `GET, POST /api/v1/projects/{project_id}/messages/` is the source of truth; WebSocket `/ws/v1/projects/{project_id}/chat/` only delivers `message.created` events. ASGI `OriginValidator` allows origins from `FRONTEND_BASE_URL` and `CSRF_TRUSTED_ORIGINS`, rejecting missing or foreign origins; `AuthMiddlewareStack` and the consumer's authenticated active-member check still apply. New sends publish after commit; replaying the same `client_message_id` does not publish again.
- `backend/apps/documents/` owns document metadata/storage, lifecycle approvals, selectors/services, and the scheduled deletion task. Project upload/list is under `/api/v1/projects/{project_id}/documents/`; document detail/download/lifecycle/restore use `/api/v1/documents/{document_id}/`; request approval/rejection/cancellation uses `/api/v1/document-lifecycle-requests/{request_id}/`. Both active members share documents. Upload supports PDF, DOCX, TXT, and Markdown up to 20 MiB. Archive and permanent deletion require both participants. The deletion window starts on second approval; restore cancels an unapproved one-party deletion request, while an approved deletion needs explicit cancellation before restore.
- `backend/apps/common/` owns safe project audit writes. Keep views thin, writes in the owning app's services, reads in selectors, and cross-app writes behind the owner service. Audit metadata must not contain tokens, credentials, message content, or file contents.
- `backend/apps/` contains domain apps and their `models.py`, `services.py`, `selectors.py`, `api/`, `migrations/`, and `tests/`. Preserve additive migrations and existing local data.

## Frontend and API contract

- Frontend FSD direction is `app -> pages -> widgets -> features -> entities -> shared`. Routes live in `frontend/src/app/App.tsx`; auth and invitation pages are in `pages/auth/` and `pages/invitations/`; project, chat, state, and questionnaire pages are in `pages/projects/`. Domain APIs/query hooks live in `entities/`; user actions live in `features/`; the authenticated shell is `widgets/workspace-shell/`.
- `frontend/src/shared/api/index.ts` owns same-origin `apiJson`, credentials, CSRF bootstrap/header, and `ApiError`. Do not put business authorization in UI or credentials in browser storage. Query hooks do not retry 4xx `ApiError`s.
- API TypeScript types are generated from drf-spectacular OpenAPI. Never edit `frontend/src/shared/api/generated/schema.d.ts` manually. After API changes, regenerate and copy the file using the commands below.
- Technical contracts and unresolved product decisions live in `docs/README.md`, `docs/`, and `docs/OPEN_DECISIONS.md`; major decisions are recorded under `docs/decisions/`.

## Checks and generated API types

Run from the repo root with the current Compose images:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend python manage.py makemigrations --check --dry-run
docker compose run --rm --no-deps backend python manage.py spectacular --validate --file /tmp/openapi.yml
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q apps/documents/tests/test_api.py
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose run --build --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm test -- src/pages/projects/ui/ProjectDocumentsPanel.test.tsx
docker compose exec frontend npm run build
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
docker compose cp frontend:/app/src/shared/api/generated/schema.d.ts frontend/src/shared/api/generated/schema.d.ts
```

The latest verified full suites for the current implementation were backend `300 passed` and frontend `72 passed / 10 files`; Ruff format/lint, migration check, drf-spectacular validation, frontend format/lint/typecheck/build, Compose config, live migrate, and `/api/v1/health/` passed. Re-run checks for changed code before reporting it as verified. Backend source is baked into its image; frontend source is baked into its image. `frontend/scripts/generate-api-types.mjs` writes the generated declaration inside the container, then `docker compose cp` copies it to the repository.
<!-- autopilot:end -->
