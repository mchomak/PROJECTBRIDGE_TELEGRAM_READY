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
# ProjectBridge: Stage 00

Stage 00 currently establishes repository setup. The React/Vite frontend, Django backend, and Docker Compose runtime are Stage 01 work. `frontend/`, `backend/`, `infra/`, and `scripts/` currently contain only `.gitkeep`; no frontend/backend source, manifests, dependency files, or app start/test/build setup exists. `.env.example` contains placeholders. `projectbridge_mvp_demo.html` is the local product/visual reference.

## Planned Stage 01 commands (unavailable in Stage 00)

The root README lists these planned commands; do not treat them as runnable until Stage 01 adds the app files and configuration:

- Frontend (`frontend/`): `npm ci`; `npm run format:check`; `npm run lint`; `npm run typecheck`; `npm test`.
- Backend (`backend/`): `python -m venv .venv`, activate it, then `python -m pip install -r requirements.txt`; checks: `ruff format --check .`, `ruff check .`, `python -m pytest`.

No application start command is available yet. `/autopilot` work is recorded in `.autopilot/`; consult only its current run instructions for task scope.
<!-- autopilot:end -->