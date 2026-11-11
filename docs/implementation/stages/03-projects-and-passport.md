# Stage 03 — Projects and Project Passport

**Goal:** Allow an authenticated executor to create and manage a project
and its initial passport.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Projects and membership
- `docs/api/API_CONTRACT.md` — Projects and passport
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`

## Dependencies

Stage 02.

## Scope

### Backend

- Implement Project, ProjectMember, and ProjectPassport models and
  migrations.
- Support the four initial project types only: `website`,
  `telegram_bot`, `automation`, `other`.
- Enforce one active executor and one active customer per project.
- Create Project, executor membership, and passport atomically.
- Implement project list, create, detail, update, member list, complete,
  and archive operations described in the API contract.
- Implement passport read and executor update.
- Add passport `version` handling and return `409 Conflict` for stale
  updates.
- Ensure all project reads and writes are scoped to active project
  membership and role.

### Frontend

- Project list page.
- Project creation flow with the four project types.
- Project overview page.
- Passport view/edit experience for executor.
- Read-only passport view for customer once a customer membership
  exists.
- Loading, empty, validation, and error states.

## Out of scope

- Customer invitation flow.
- Questionnaire and passport auto-population.
- Project State entities.
- Progress percentages.
- Public freelance-order import.

## Deliverables

- Project and membership models.
- ProjectPassport model and service layer.
- Project and passport API endpoints.
- Project list/create/detail UI.
- Permission and concurrency tests.

## Acceptance criteria

- [ ] A verified authenticated user can create a project.
- [ ] Project, executor membership, and passport are created in one
  transaction.
- [ ] Only the four agreed project types are accepted.
- [ ] A user sees only projects where they are an active member.
- [ ] Only the executor can update project metadata and passport
  directly.
- [ ] Both project participants can read the passport.
- [ ] A stale passport update returns `409 Conflict` and does not
  overwrite newer data.
- [ ] Duplicate active executor/customer memberships are prevented.
- [ ] Tests cover cross-project access and role violations.

## Stop conditions

The exact passport field set must follow `DATA_MODEL.md` and the
questionnaire mapping decisions. If the current product document defines
different required fields, surface the discrepancy instead of silently
adding/removing fields.

## Codex handoff

Implement Stage 03 only. Build the project and passport vertical slice,
including UI, API, migrations, permissions, and tests.
