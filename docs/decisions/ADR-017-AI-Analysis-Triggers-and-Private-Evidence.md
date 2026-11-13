# ADR-017: Manual AI Analysis and Private Evidence

**Status:** Accepted for the MVP
**Date:** 2026-11-13

## Context

Stage 11 requires AI analysis and contradiction proposals, while the exact
automatic triggers and chat batching policy were open. AI must remain
advisory, preserve source provenance, and never mutate shared Project State
without executor approval. Project State Evidence is shared when attached to
a shared conflict, so writing AI review excerpts there before approval would
blur the privacy boundary.

## Decision

- Only an executor with an active project membership may start an analysis.
  The project must be in `draft` or `active` status; `completed` and
  `archived` projects reject analysis. Each analysis is started manually
  through the AI workspace.
- Questionnaire submissions, chat messages, document processing, and Project
  State changes do not trigger analysis. Chat debounce/batching is not needed
  while message-triggered analysis is disabled.
- The API creates a durable request before enqueueing the Celery task. A
  caller-provided `Idempotency-Key` UUID scoped to project and executor makes
  POST retries return the same request. Requests expose only queued, running,
  succeeded, or failed state and safe error codes.
- Celery claims use a six-minute lease and a monotonically increasing
  generation. A delivery that finds an active lease retries after a short
  delay. A delivery may reclaim an expired lease; a previous generation
  cannot commit proposals or mark the request complete.
- AI-time evidence references and excerpts stay in AI-owned request and
  proposal evidence tables. They are not Project State Evidence and are
  readable only through executor-only AI endpoints.
- The Project State service validates executor role, project scope, source
  eligibility, and same-project ownership when resolving AI evidence. Before
  any proposal is applied, every linked source is resolved again and its
  excerpt and metadata must match the AI-time snapshot inside the application
  transaction. Only then may the owning Project State service write. Conflict
  application also passes the expected snapshots to the Project State service,
  which creates shared Evidence and the conflict together after its own check.
- The AI must cite only source references supplied in its bounded context. A
  conflict proposal requires at least two distinct references and does not
  select a preferred value. Invalid or stale evidence leaves the proposal
  pending and does not change shared state.
- Deterministic questionnaire conflicts remain in their separate
  executor-only questionnaire queue.

## Consequences

- MVP analyses are explicit user actions; no provider calls are triggered by
  ordinary collaboration events.
- A retried task cannot publish duplicate visible proposals. If a worker dies
  after a provider call but before the database transaction commits, an
  expired lease may cause another provider call; only the current fenced
  generation can publish results. Each provider call remains separately
  recorded by the AI Router.
- Source values that change before proposal approval cause application to
  fail and require a new analysis or review, preserving what the executor saw
  in the proposal.
- Any future automatic trigger must specify its duplicate prevention,
  batching/debounce, and cost policy before it is enabled.
