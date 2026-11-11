# ADR-007: Shared Documents with Mutual-Consent Lifecycle

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

ProjectBridge is a collaborative workspace. The executor and customer
must work with the same project documents. Accidental unilateral removal
would undermine the shared project record.

## Decision

- All documents are shared with both participants.
- Both participants can upload.
- Private documents are not supported.
- Archive and permanent deletion require consent from both participants.
- The initiator’s request records their approval; the other participant
  must approve.
- Archived documents can be restored by either participant.
- Permanent deletion has a 30-day cancellation window after both
  approvals.
- Source files and derived text/chunks/embeddings are removed together.

## Consequences

- Document visibility is not represented by a private/shared field.
- Document lifecycle is an explicit state machine.
- RAG excludes archived and deletion-pending documents.
- Backup expiry may lag behind live deletion and must be disclosed.
