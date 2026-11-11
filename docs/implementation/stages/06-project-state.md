# Stage 06 — Project State

**Goal:** Implement the shared structured view of project delivery:
stages, requirements, tasks, open questions, and conflicts.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Project State and Evidence
- `docs/api/API_CONTRACT.md` — Project State
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/OPEN_DECISIONS.md` item 5

## Dependencies

Stages 03 and 05.

## Required product decision

Confirm the statuses and allowed state transitions for stages,
requirements, tasks, open questions, and conflicts before implementing
state-transition logic.

## Scope

### Backend

- Implement ProjectStage, Requirement, Task, OpenQuestion,
  ProjectConflict, and Evidence models.
- Add project-scoped selectors and service operations.
- Implement the Project State aggregate read endpoint.
- Implement CRUD/action endpoints listed in the API contract.
- Enforce executor-only create/update operations.
- Allow both executor and customer to read all shared Project State
  entities.
- Preserve source evidence and provenance for conflicts.
- Ensure AI analyses and pending AI proposals are never included in the
  shared Project State aggregate.
- Do not add completion percentage fields or calculated percentage
  responses.

### Frontend

- Shared Project State view for both roles.
- Executor controls for creating and editing stages, requirements,
  tasks, questions, and conflict resolutions.
- Customer read-only view.
- Clear status and due-date presentation.
- No progress percentage or unsupported completion score.

## Out of scope

- Customer editing of structured Project State.
- Automatic AI updates.
- Advanced project analytics or Gantt scheduling unless explicitly added
  later.
- Percent-complete calculations.

## Deliverables

- Project State models and migrations.
- Services, selectors, API endpoints, and permissions.
- Executor editing UI and customer read-only UI.
- Evidence/provenance handling.
- State transition and access-control tests.

## Acceptance criteria

- [ ] Both participants can read every shared Project State entity in
  their project.
- [ ] Only the executor can create or modify structured Project State
  entities.
- [ ] A customer cannot modify state by calling the API directly.
- [ ] Cross-project IDs cannot be used to read or mutate another
  project’s records.
- [ ] Conflict records retain source references and resolution history.
- [ ] AI-only analyses and proposals are excluded from customer
  responses.
- [ ] No completion percentage is stored or displayed.
- [ ] All implemented status transitions match the approved state
  machine.
- [ ] Tests cover role boundaries, invalid transitions, and project
  isolation.

## Stop conditions

Stop if the status model, conflict visibility, or evidence ownership is
ambiguous. Do not create a broad generic workflow engine; implement only
the agreed Project State entities and transitions.

## Codex handoff

Implement Stage 06 only. The customer must have full read access to
shared Project State and no direct structured write access.
