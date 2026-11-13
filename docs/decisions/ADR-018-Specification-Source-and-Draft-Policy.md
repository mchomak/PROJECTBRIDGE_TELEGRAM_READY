# ADR-018: Specification Draft and Generation Source Policy

**Status:** Accepted for the MVP
**Date:** 2026-11-13

## Context

Stage 12 needs a concrete source policy, unresolved-information handling,
output format, editing behavior, and MVP priority before specification
generation can be implemented. ProjectBridge already has an authoritative
executor-maintained passport and shared Project State. Chat, documents/RAG,
and pending AI proposals have different authority and privacy properties;
there is no product policy allowing them to become specification facts.

## Decision

- Keep one shared editable Markdown draft per project. A draft is an
  available MVP workflow and is not required to create or complete a project.
- Use only the project passport and shared Project State as generation
  sources. Read them through their owning-app selectors. Exclude chat,
  documents/RAG, private AI analyses, and pending AI proposals.
- Include only the passport and Project State records, not project name or
  description. Mark draft requirements unconfirmed, rejected requirements
  excluded, cancelled stages/tasks excluded from the current plan, and done
  tasks/completed stages as historical rather than future work. Preserve each
  shared record's status label in the context.
- Include shared open questions and conflicts with explicit unresolved
  labels. The generator must not choose a side of an unresolved conflict or
  present either claim as fact. Dismissed issues remain non-authoritative;
  resolved conflicts are represented only by their recorded resolution.
  Missing values are marked as not specified.
- Both active project members can read the current draft. Only the active
  executor can generate or edit, and only while the project is `draft` or
  `active`. Completed and archived projects are read-only.
- Store one current Markdown body and increment its optimistic `version` on
  every executor edit and successful generation. Do not retain formal
  versions, comments, customer redlines, approvals, or signatures.
- Queue generation through Celery and the AI Router task key
  `specification_generation`. Require an executor-scoped idempotency key and
  fence workers by request generation and specification version.
- Close the database-commit/queue-dispatch crash gap with a Celery Beat
  recovery sweep every 60 seconds. Persist dispatch attempts, publish
  exceptions, an ambiguous/success marker, and a two-minute dispatch lease;
  reserve redispatch under a row lock and reuse the original request and Celery
  task IDs. Concurrent sweepers therefore reserve only one dispatch at a time.
  Publish exceptions are ambiguous because an error can follow broker
  acceptance. Cap the stored exception count at 12 and use exponential backoff
  from 30 seconds to 30 minutes; after five exceptions expose
  `queue_unavailable` while keeping the request queued, then
  continue automatic recovery with the same task ID until worker claim or
  explicit cancellation. Neither exception count nor publish attempts fence a
  message that may already be queued. After five dispatch reservations without
  a worker claim, expose nonterminal `worker_backlog`; worker claim clears both
  warnings. Worker claims and execution fencing remain required for every
  delivery.
- At enqueue, hash a canonical structured context. Do not persist the raw
  context or complete prompt. Rebuild and compare the hash after prompt
  assembly immediately before the model call, and again before publication.
  Keep these checks in short transactions and do not hold a database lock
  during the provider call. If source data changes before the call, mark the
  request superseded without sending stale input; if it changes during
  generation, discard the output. If the executor edits while generation
  runs, the edit wins.
- Cap the worker's complete request at 24,000 UTF-8 bytes, within the router
  profile's 32,000-byte limit. Use normal router cost reservations and
  provider limits; tests stub the router and never call paid providers.

## Consequences

- The specification remains a draft artifact, not a legal or customer-
  approved document. The feature is available but does not block project
  creation or completion.
- RAG and other source inclusion require a future explicit authority,
  privacy, and disclosure policy before they can be added.
- Snapshot hashes retain no source text, but are sufficient to detect that
  queued work no longer corresponds to the current shared structured data.
- If a process exits after the request commits but before its `on_commit`
  callback sends Celery work, the Beat sweep finds the stale queued row. If a
  redispatch races with an already sent task, request-level row locks, worker
  leases, and fencing make the duplicate delivery a no-op or lease wait; it
  does not create another generation request.
- A source can still change after the final pre-call check while the model is
  running; the publish check fences that result from the shared draft.
- As with other at-least-once external provider tasks, a worker crash after
  the provider has completed but before database publication can cause a
  retry and another provider charge. Fencing prevents stale output from
  publishing; it cannot make the external model call exactly once.
