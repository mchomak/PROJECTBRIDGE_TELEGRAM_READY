# Stage 11 — AI Analysis, Contradiction Detection, and Proposals

**Goal:** Use AI and project evidence to identify missing or
contradictory information and prepare proposals for executor review
without changing shared project data automatically.

## Read first

- `AGENTS.md`
- `docs/ai/AI_ARCHITECTURE.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — AIAnalysisRun, AIProposal, Evidence
- `docs/api/API_CONTRACT.md` — AI Assistant
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/OPEN_DECISIONS.md` items 16 and 19

## Dependencies

Stages 05, 06, 07, 09, and 10.

## Required decisions

Confirm automatic analysis triggers and chat batching/debounce behavior.
Confirm the visibility workflow for deterministic questionnaire
conflicts separately from AI-generated proposals.

## Scope

### Analysis orchestration

- Implement asynchronous analysis runs through Celery.
- Support executor-triggered analysis.
- Add only those automatic triggers that have been explicitly approved.
- Use task-specific AI profiles through the AI Router.
- Gather context from approved project sources and RAG retrieval.
- Keep analysis scoped to the current project.

### Contradiction detection

- Detect potentially conflicting statements from project sources.
- Preserve both source values and source references.
- Explain why the statements may conflict.
- Do not infer which source is correct.
- Store results as executor-only AI proposals pending review.

### Proposal workflow

- Implement proposal list/detail and evidence display.
- Allow executor to accept, reject, or edit a proposal.
- Validate proposed payloads using the owning Project State service.
- Apply accepted proposals transactionally.
- Make application idempotent.
- Keep a proposal pending or failed if application does not succeed;
  never mark it applied prematurely.
- Record who reviewed/applied it and when.

### Privacy

- AIAnalysisRun and pending AIProposal data are executor-only.
- Customer-facing endpoints must not expose AI analyses, prompts,
  internal reasoning, or pending proposals.
- Once an approved change is applied to Project State, the resulting
  shared state is visible to both participants.

### Frontend

- Executor-only analysis history and proposal inbox.
- Show evidence and source references.
- Provide accept, reject, and edit-before-apply actions.
- Customer UI must not expose the AI workspace.

## Out of scope

- AI autonomously resolving contradictions.
- Automatic writes to passport or Project State.
- Customer access to AI analysis/proposals.
- AI-generated questionnaire schemas.
- Unapproved automatic analysis triggers.

## Deliverables

- Analysis orchestration and tasks.
- Contradiction detection task.
- AI proposal model/service/API.
- Evidence linking.
- Executor review UI.
- Tests for privacy, proposal review, and transactional application.

## Acceptance criteria

- [ ] AI analysis runs asynchronously and records the selected task
  profile.
- [ ] Contradictions preserve both sources and their provenance.
- [ ] AI does not decide which source is correct.
- [ ] AI never changes shared Project State without executor approval.
- [ ] Accept/reject/edit operations are executor-only.
- [ ] Applying a proposal validates and uses the owning domain service.
- [ ] Proposal application and state mutation are transactional and
  idempotent.
- [ ] Customers cannot retrieve analyses or pending proposals through
  REST or WebSocket.
- [ ] Evidence shown to the executor resolves to the correct project
  source.
- [ ] Tests cover permission bypass, failed application, duplicate
  application, and conflicting evidence.

## Stop conditions

Stop if the task requires an unselected model, undocumented analysis
trigger, or ambiguous source-priority rule. Do not hard-code assumptions
about which message is authoritative.

## Codex handoff

Implement Stage 11 only. AI output is advisory; executor approval is
mandatory before shared state changes.
