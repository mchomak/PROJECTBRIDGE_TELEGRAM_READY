# Stage 05 — Customer Questionnaire

**Goal:** Let the customer complete a project-type-specific
questionnaire and safely transfer confirmed information into the project
passport.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Questionnaire
- `docs/api/API_CONTRACT.md` — Questionnaire
- `docs/OPEN_DECISIONS.md` items 1–3 and 19
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`

## Dependencies

Stages 03 and 04.

## Required product decisions before implementation

Do not begin the full questionnaire implementation until the product
owner has confirmed:

1.  The exact questions and branching rules for all four project types.
2.  Required fields and validation rules.
3.  Versioning and compatibility rules for questionnaire schemas.
4.  Exact answer-to-passport mapping rules.
5.  Whether correction requests reopen a submission or create a new
    superseding submission.
6.  Where deterministic questionnaire/passport conflicts are shown and
    how the executor resolves them.

Record the decisions in the relevant documentation before asking Codex
to implement them.

## Scope

### Backend

- Store questionnaire definitions as versioned JSON files in the backend
  repository.
- Do not store editable questionnaire definitions in the database unless
  the architecture is explicitly changed.
- Implement deterministic schema selection and branching by project
  type.
- Prefill applicable answers from the passport.
- Store questionnaire answers separately from the passport.
- Track answer origin (`prefilled` or `customer`) and confirmation
  state.
- Validate all answers server-side.
- Lock a submitted questionnaire.
- Support the approved correction/resubmission workflow without
  destroying historical submissions.
- On submission, apply only the documented deterministic mapping rules.
- Preserve both source values when a mapping detects a conflict. Never
  silently overwrite a conflicting passport value.
- Make submission and passport updates transactional.

### Frontend

- Customer questionnaire flow with branching and prefilled values.
- Save draft answers.
- Review and submit.
- Show submitted/locked state.
- Support correction/resubmission only according to the approved
  workflow.
- Executor view of submission status and unresolved conflicts.

## Out of scope

- AI-generated questions or branching.
- AI deciding which answer is correct.
- Manual questionnaire builder for executors.
- Arbitrary executor-added questions.
- Automatic passport overwrites when sources conflict.

## Deliverables

- Versioned questionnaire schemas for the four project types.
- Questionnaire validation and mapping services.
- Submission/answer models and migrations.
- Customer questionnaire UI.
- Executor review UI for conflicts.
- Tests for branching, validation, submission locking, mapping, and
  conflicts.

## Acceptance criteria

- [ ] The correct questionnaire schema is selected for each project
  type.
- [ ] Branching is deterministic and validated by the backend.
- [ ] Prefilled answers are distinguishable from customer-provided
  answers.
- [ ] Answers are stored separately from passport fields.
- [ ] Submission is atomic and locks the submitted version.
- [ ] Passport changes follow only the approved mapping table.
- [ ] Conflicting values and their sources are preserved.
- [ ] No conflicting value is silently overwritten.
- [ ] Correction/resubmission preserves historical submitted data.
- [ ] AI is not used to generate or branch questionnaire questions.
- [ ] Tests cover every schema branch and conflict behavior.

## Stop conditions

If the exact schemas, mapping table, conflict visibility, or correction
workflow is missing, stop and ask for the product decision. Do not
invent questions or infer field mappings from labels.

## Codex handoff

Implement Stage 05 only after the questionnaire decisions have been
recorded. Treat the versioned schemas and mapping table as authoritative
product inputs.
