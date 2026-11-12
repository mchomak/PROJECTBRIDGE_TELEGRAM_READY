**ADR-010: Optimistic concurrency for passport updates**

## Context

An executor edits a project passport through a form that may remain open while another update changes the stored passport. The user requirement is to avoid overwriting changes made after that form was loaded.

## Decision

Require the current passport `version` on each PATCH. Compare the supplied version and save the requested field changes atomically; increment the version on success. Reject a stale version with `409 Conflict` and make no changes.

## Why

Last-write-wins updates would silently replace newer passport data with a stale form submission, contrary to the stated no-overwrite requirement. Version checking detects that race without requiring a locking session across the user’s editing time.

## Consequences

Clients must submit the version they read and handle `409` by offering to load the current passport. The UI can preserve unsaved text until the user explicitly reloads; successful edits advance the version by one.
