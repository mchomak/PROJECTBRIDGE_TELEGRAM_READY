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
  reopen, archive, and restore operations described in the API contract.
- Create projects in `draft`; enforce the documented lifecycle transitions,
  including `status_before_archive` storage and restore behavior.
- Implement passport read and executor update.
- Add passport `version` handling and return `409 Conflict` for stale
  updates.
- Ensure all project reads and writes are scoped to active project
  membership and role.

### Frontend

- Project list page with a separate archived-project section.
- Project creation flow with the four project types.
- Project overview page with lifecycle status and allowed executor
  actions.
- Passport view/edit experience for executor while the project is
  `draft` or `active`.
- Read-only passport view for both participants when the project is
  `completed` or `archived`.
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
- [ ] A new project has status `draft`; the `draft`-to-`active`
  invitation transition is owned and tested by Stage 04.
- [ ] Only the executor can complete, reopen, archive, or restore a
  project; invalid transitions return `409 Conflict`.
- [ ] Completion is allowed only from `active`; reopening changes
  `completed` to `active`.
- [ ] Archiving accepts `draft`, `active`, or `completed`, stores the
  prior status, and restoration returns to that status and clears
  `status_before_archive`.
- [ ] Archived projects are omitted from the main list and available in
  the separate archive list.
- [ ] Both participants can read completed and archived project data;
  project metadata and passport writes are rejected in those statuses.
- [ ] Archiving preserves memberships, project data, and documents; no
  automatic deletion is scheduled for completed or archived projects.

## Stop conditions

Use exactly the approved ProjectPassport field names and types in
`DATA_MODEL.md`; do not add or remove business fields. Do not infer
questionnaire requiredness or answer mappings in Stage 03. Those remain
Stage 05 decisions.

## Codex handoff

Implement Stage 03 only. Build the project and passport vertical slice,
including UI, API, migrations, permissions, and tests.
