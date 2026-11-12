# ADR-008: Project-Scoped Roles and Shared Project State

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

The executor manages delivery and internal AI work. The customer needs
transparency into the project but should not see internal AI analysis or
unreviewed AI proposals.

## Decision

- Roles are project-scoped: executor and customer.
- Both participants can read all shared Project State.
- Only the executor can create or modify structured Project State.
- Both participants can read and upload all project documents.
- AI analysis runs and AI proposals are executor-only.
- The customer contributes through chat and questionnaire responses.
- Project lifecycle access follows the status rules in
  `docs/security/ACCESS_CONTROL_AND_SECURITY.md`: `completed` and
  `archived` are read-only for both participants, with executor-only
  reopen/archive/restore actions as permitted by the current status.
- Project archival preserves active memberships and data. The previous
  status is stored and restored; archival is not deletion.
- Accepting a customer invitation moves a `draft` project to `active`
  through the invitation service. Clients cannot directly set status.

## Consequences

- The backend enforces role and resource permissions on every endpoint.
- Customer-facing Project State responses exclude AI internals.
- Frontend visibility rules are not considered security controls.
- Project membership is checked for REST and WebSocket access.
- Lifecycle state restrictions are enforced by backend services and
  permissions, not by frontend visibility alone.
