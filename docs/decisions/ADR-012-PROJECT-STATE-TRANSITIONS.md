# ADR-012: Project State Entities and Transitions

- **Status:** Accepted
- **Date:** 2026-11-12
- **Decision owners:** Project owner

## Context

Project State needs explicit, auditable lifecycles for shared stages,
requirements, tasks, questions, and conflicts. Generic workflow rules
would make these domain contracts harder to validate and could expose
unapproved project progress behavior. The Stage 04-08 Autopilot
specification §3 defines the approved states and transitions.

## Decision

The `project_state` app owns `ProjectStage`, `Requirement`, `Task`,
`OpenQuestion`, `ProjectConflict`, `Evidence`, and their links. Domain
services validate these exact transition tables and commit state changes
with content-free audit metadata:

| Entity | Allowed transitions |
|:--|:--|
| `ProjectStage` | `planned -> active, cancelled`; `active -> blocked, completed, cancelled`; `blocked -> active, cancelled` |
| `Requirement` | `draft -> confirmed, rejected`; `confirmed -> in_progress, rejected`; `in_progress -> blocked, completed, rejected`; `blocked -> in_progress, rejected` |
| `Task` | `todo -> in_progress, cancelled`; `in_progress -> blocked, done, cancelled`; `blocked -> in_progress, cancelled` |
| `OpenQuestion` | `open -> resolved, dismissed` |
| `ProjectConflict` | `unresolved -> resolved, dismissed` |

States with no outgoing edge are terminal. In particular, completed,
cancelled, rejected, resolved, and dismissed records cannot be reopened.
For terminal `ProjectStage`, `Requirement`, `Task`, and `OpenQuestion`
records, terminality closes the status lifecycle but does not freeze
content: executors may update supported content fields while omitting
`status`. Any update that supplies `status` for these terminal records
is rejected. `ProjectConflict` is stricter: after it becomes `resolved`
or `dismissed`, it is immutable and every subsequent update is rejected.
The UI omits status selectors on terminal records, keeps content edits
available for terminal stages, requirements, tasks, and questions, and
hides conflict edit controls after resolution or dismissal.
Writes require an executor and a project in `draft` or `active`; active
project members can read shared Project State. Conflict resolution stores
the resolving actor, time, and resolution. Audit metadata stores IDs,
changed field names, and status transitions, not user-entered content.

`Evidence` stores immutable source snapshots. Stage 06 resolves only
questionnaire answer sources through the questionnaire-owned selector;
the message source resolver is added by the chat stage once its model and
selector exist. A shared conflict links at least two distinct sources
from the same project. Questionnaire-to-passport mapping conflicts stay
in the executor-only `QuestionnaireConflict` queue and do not create a
shared `ProjectConflict` automatically.

## Consequences

- The entity state machines stay explicit and small; there is no generic
  workflow engine, Gantt representation, or completion percentage.
- Invalid or terminal transitions return a conflict response and cannot
  create a successful audit event.
- Reads remain project-scoped; customers cannot create or edit these
  structured records.
- Evidence provenance is extensible by its owning app selector while
  preserving a verified project boundary.
