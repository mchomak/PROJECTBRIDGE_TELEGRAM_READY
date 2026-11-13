# Stage 12 — Specification Draft

**Goal:** Generate and maintain an editable project specification draft
using approved project context.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Specification
- `docs/api/API_CONTRACT.md` — Specifications
- `docs/ai/AI_ARCHITECTURE.md`
- `docs/OPEN_DECISIONS.md` item 7

## Dependencies

Stages 05, 06, 09, 10, and 11.

## Required product decisions

Before implementation, confirm: - which sources are included in
generation; - how unresolved questions/conflicts are represented; -
output format and structure; - whether generation is a single draft or
supports versions; - whether this feature is mandatory for MVP
acceptance.

Formal customer approval, comments, signing, and approval workflow
remain out of scope.

### Resolved for this stage (2026-11-13; ADR-018)

- Keep one shared, editable Markdown draft per project. Draft availability
  is part of the MVP workflow, but a draft is not required to create or
  complete a project.
- Generate asynchronously from the approved project passport and shared
  Project State only. Do not use chat, documents/RAG, internal AI analyses,
  or pending AI proposals.
- Preserve open questions and unresolved conflicts as explicitly unresolved;
  do not assert either side of a conflict as fact.
- Both active project members can read. Only the executor can generate and
  edit while the project is writable. Completed and archived projects are
  read-only.
- Enforce optimistic version checks and discard generation results if the
  draft or source snapshot changes before publication.

## Scope

### Backend

- Implement the Specification model and version/concurrency behavior
  described in the approved contract.
- Generate a draft asynchronously through the AI Router using
  `specification_generation`.
- Use approved passport and Project State data as the authoritative
  structured context.
- Use documents/RAG only according to the confirmed source policy.
- Do not silently treat pending AI proposals or unresolved
  contradictions as approved facts.
- Allow the executor to edit the draft.
- Allow both participants to read the current specification.
- Enforce executor-only generation and editing.

### Frontend

- Specification read view for both participants.
- Executor generation action and progress/status state.
- Executor editor.
- Conflict/error state if the underlying specification version changes
  concurrently.

## Out of scope

- Customer approval.
- Electronic signatures.
- Customer comments or redlines.
- Legal document automation.
- Formal approval workflows.

## Deliverables

- Specification model and migrations.
- Generation task and service.
- API endpoints.
- Executor editor and customer read view.
- Version/concurrency tests.

## Acceptance criteria

- [ ] Only the executor can generate or edit the specification.
- [ ] Both participants can read the current specification.
- [ ] Generation uses the approved task profile through the AI Router.
- [ ] Only approved project information is treated as authoritative.
- [ ] Unresolved conflicts are not silently converted into facts.
- [ ] Long-running generation is asynchronous.
- [ ] Concurrent edits do not silently overwrite newer versions.
- [ ] Tests cover role permissions, generation failure, and stale
  updates.

## Stop conditions

If generation inputs, output format, or MVP priority are not confirmed,
stop before implementing the generation workflow. Do not invent a formal
approval feature.

## Codex handoff

Implement Stage 12 only after the specification contract has been
confirmed. Keep this feature to draft generation and executor editing.
