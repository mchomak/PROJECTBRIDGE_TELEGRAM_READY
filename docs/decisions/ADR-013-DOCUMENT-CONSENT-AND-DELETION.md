# ADR-013: Document Consent and Scheduled Deletion

- **Status:** Accepted
- **Date:** 2026-11-12
- **Decision owners:** Project owner

## Context

Project documents are shared. Removing one participant’s file without the
other’s consent would break the shared project record. The prior
document contract did not enforce that permanent deletion starts only
after archive, nor did it clearly anchor the 30-day cancellation window
to the second approval. A consented live deletion must also finish after
the parent project later becomes read-only, without claiming immediate
backup erasure.

## Decision

- Archive and permanent deletion are separate two-party actions. The
  initiator’s approval is recorded with the request; both active project
  roles must exist. Requests and second-party decisions require a
  `draft` or `active` parent project.
- Archive is available only from `active`: request moves the document to
  `archive_pending`; rejection returns it to `active`; approval moves it
  to `archived`. Pending archive documents remain in the active list but
  are excluded from retrieval.
- Permanent deletion is available only from `archived`. The document
  stays archived until the second participant approves. That approval
  moves it to `deletion_pending` and sets `deletion_after` to exactly 30
  days later.
- Either active project member may cancel strictly before the deadline.
  Cancellation returns the document to `archived`; restoration to
  `active` is a separate member action, allowed only when the parent
  project is `draft` or `active`.
- Restoring an archived document while a permanent-delete request is
  still pending after only the initiator's approval cancels that request
  in the same transaction and audits both actions. A deletion already
  approved by both participants must be explicitly cancelled before
  restore.
- Cancellation remains available before the deadline after the parent
  project has completed or been archived. An uncancelled approved
  deletion completes when due even after those project transitions.
- One Celery Beat service schedules an idempotent sweep every five
  minutes through the existing Redis broker. The task removes source
  bytes and existing Stage 08 derivatives, scrubs content-bearing
  metadata, marks the document deleted, and writes a content-free audit
  event. Stage 09 must extend cleanup for chunks and embeddings before
  extraction is enabled.
- Encrypted backups may retain deleted files until their applicable
  operational expiry. No fixed backup expiry or immediate purge from all
  backup copies is promised.

## Consequences

- Document services enforce the state machine under project/document
  locks; API views only validate and map domain errors.
- The document row and explicit consent records remain as a minimal
  tombstone/audit trail. The source filename, MIME type, size, and content
  digest are cleared after deletion; the private storage key is retained
  for uniqueness and never exposed.
- Archived and deletion-pending documents are absent from the active
  list and retrieval. Restoring an archived document makes it active
  again; cancelled deletion does not restore it automatically.
- Project completion/archive does not revoke prior deletion consent or
  prevent a member from withdrawing it before the deadline.
