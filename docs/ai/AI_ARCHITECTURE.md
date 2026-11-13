# ProjectBridge AI Architecture

**Status:** Router and initial OpenAI model profiles implemented for the local MVP
**Last updated:** 2026-11-13

## 1. Requirements

AI integration must be provider-independent and configurable per task.
The system must not hard-code one provider or one model across the
product.

Different functions may use different providers and models, including:

- low-cost models for lightweight message analysis;
- stronger models for conversation-level reasoning and contradiction
  analysis;
- embedding models for vectorization;
- rerankers for retrieval refinement;
- stronger generation models for specification generation.

Changing a provider or model for one task must not require changes to
business-domain logic.

## 2. AI Router

All AI operations go through an internal AI Router. Domain modules call
the router using a stable task key and typed input/output contract.

The caller identifies the operation, not the provider or model. The
router resolves the active profile, checks required capabilities,
selects a compatible provider adapter, executes the operation, records
usage, and returns a normalized result.

Initial task keys:

- `message_analysis`
- `conversation_analysis`
- `contradiction_detection`
- `document_embedding`
- `rag_reranking`
- `specification_generation`

Additional tasks may be introduced without changing the domain-level
calling pattern.

## 3. Provider adapters and capabilities

Do not assume every provider supports every AI operation. Use separate
capability interfaces, such as:

- text generation;
- embeddings;
- reranking.

A provider adapter declares the capabilities it supports. The router
must reject an incompatible profile before execution.

Provider-specific request/response formats, authentication, retries, and
error mapping belong inside adapters. Business modules must not import
provider SDKs directly.

## 4. Model profiles

Store task-level model configuration in `AIModelProfile`, editable
through restricted backend administration in the MVP.

A profile contains:

- task key;
- provider key;
- model identifier;
- supported capabilities;
- generation/retrieval parameters;
- enabled state;
- configuration version;
- optional compatible fallback profile.

Provider credentials are not stored in the database. They are read from
environment configuration or a production secret manager.

The initial local profiles use OpenAI. `message_analysis` uses
`gpt-6-luna` with `gpt-6.1-sol` as a compatible fallback;
`conversation_analysis`, `contradiction_detection`, and
`specification_generation` use `gpt-6.1-sol` with `gpt-6-luna` as a
fallback. `document_embedding` uses `text-embedding-3-small` at 1536
dimensions. `rag_reranking` uses a strict structured-scoring adapter on
`gpt-6.1-sol`, with `gpt-6-luna` as fallback. The adapter returns one
validated score for every candidate; the router orders candidates by
score and rejects missing, duplicate, out-of-range, or non-finite results.
Profiles and their compatible fallbacks can be changed by backend staff
in Django Admin.

The adapter uses the official OpenAI Python SDK and Responses API. A
missing key, denied model, malformed response, or provider outage is
returned as a stable error code. The SDK's internal retries are disabled;
the router makes one bounded retry for transient rate-limit, timeout,
connection, or server errors, then tries only a capability-compatible
fallback. Authentication, permission, invalid-request, and missing-model
errors do not trigger fallback.

Default task budgets are editable profile parameters: at most USD 1.00
reserved per task per UTC day, USD 0.25 per generation/reranking request,
and USD 0.10 per embedding request. Each profile also caps input bytes,
candidate count, output tokens, and provider timeout. A PostgreSQL
transaction-scoped advisory lock serializes reservations across every
profile for the same task. The router reserves the estimated maximum
before each primary, retry, or fallback provider call and accumulates all
attempt reservations against the request and task-day ceilings. The
request/day ceilings are snapshotted from the primary profile for the call
chain; a fallback may lower the request ceiling but cannot raise either
limit. `reserved_cost` is never reduced when a later call succeeds or
fails. `estimated_cost` stays at least as high as that cumulative
reservation. If returned usage exceeds its attempt reservation, the known
excess is added to the daily total under the same lock. Rates are
configuration snapshots, not a quote or a hard limit on charges incurred
outside this application.

Callers supply a prompt version label. The router stores that label, a
SHA-256 input hash, provider/model/profile version, status, timing, token
usage, attempt count, and estimated cost; it does not persist prompts or
source text. Profiles and run metadata are staff-only in Django Admin.

Fallback profiles must serve the same task and required capability. Text
generation profiles share the same typed request/response contract.
Embedding fallback additionally requires the same provider, model,
dimensions, and embedding-space version. `EmbeddingBatch.profile_key` is a
stable hash of provider, exact model identifier, and dimensions; its
`profile_version` is the separate `embedding_space_version`. Routing
changes such as timeout, cost rates, or fallback selection only increment
`config_version` and do not hide vectors. Do not silently fall back to a
different model, even if it has the same dimension.

## 5. RAG pipeline

RAG is a pipeline, not a single model call.

1.  Extract text from supported documents.
2.  Split extracted text into chunks.
3.  Generate embeddings using the active embedding profile.
4.  Store chunks and vectors in PostgreSQL/pgvector.
5.  Embed the search query using a compatible embedding profile.
6.  Retrieve candidate chunks using vector search and, if required,
    metadata filters.
7.  Optionally rerank candidates using the configured reranking profile.
8.  Pass selected evidence to the task-specific generation model.
9.  Return an answer or analysis with source references.

The initial embedding profile is OpenAI `text-embedding-3-small` with
1536 dimensions. Chunks contain at most 1000 Unicode characters with 150
characters of overlap. PDF chunks stay within a page and record the page
number; DOCX chunks stay within a paragraph and record its index; TXT and
Markdown chunks record character offsets. Retrieval uses cosine distance
and returns the five nearest chunks by default, with an explicit
project-member scope and active-document filter. The reranking capability
is configurable, but retrieval does not invoke it automatically in Stage
09. A result is available only when the query embedding has the same
embedding-space key, embedding-space version, and returned model name as
the indexed chunks. Cost/timeout profile revisions do not change that
tuple, and different models never share it.

### Embedding compatibility

Vectors from different embedding models or incompatible dimensions must
not be mixed in one search operation. The embedding-space key is derived
from provider, exact model identifier, and dimensions. Bump
`embedding_space_version` when the provider changes the vector space
behind a stable identifier or when vector-affecting settings change.
Ordinary routing configuration edits do not affect this version.

The current document processor stores one active chunk set per document;
it does not provide shadow-index backfill or atomic cutover. Changing the
active provider/model therefore requires a maintenance window: pause
retrieval, change the embedding profile, then run
`python manage.py reindex_document_embeddings --project-id <uuid>` (or
`--all-projects`) to queue the documents-owned retry-safe reindex task.
The command includes active and archived documents and excludes
lifecycle-pending, deleted, and unsupported documents. Failed tasks retry
up to three times; rerunning the command is safe. Resume retrieval only
after every eligible document is `ready` with embeddings for the new
key/version/model. Reindexing replaces derived chunks and vectors only;
source files and user-confirmed project data are unchanged. Existing
vectors are never mixed with the new model; searches during the maintenance
window are unavailable. A dimension change requires a shadow vector
column or table and an explicit migration before such a switch.

OpenAI limits each embedding input to 8,192 tokens, each request to 2,048
items, and each request to 300,000 total tokens. The router also enforces a
200,000 UTF-8-byte request ceiling or the lower profile cost limit, plus an
8,192-byte per-input ceiling. Document reindexing batches by both count and
bytes. It assembles all batch responses before the atomic derived-row
replacement and rejects the run if any batch changes the exact vector-space
key, version, or model.

## 6. AI analysis and proposals

AI analysis creates an `AIAnalysisRun`. Results that suggest changes to
project data are stored as `AIProposal` records.

A proposal includes:

- proposal type;
- title and description;
- rationale;
- proposed structured payload;
- source evidence;
- review status.

AI proposals and analysis runs are private to the executor. They are not
returned by customer-facing project endpoints.

Before approval, source references and immutable excerpts belong to the
AI-owned request/proposal evidence tables. They do not create `project_state`
`Evidence` rows or otherwise change shared Project State. Evidence source
resolution goes through Project State's service boundary, which validates the
active executor, project ownership, and source lifecycle. When an executor
applies a conflict proposal, the Project State service re-resolves each source
inside the application transaction and compares it with the AI-time excerpt and
metadata. If a source changed or is no longer eligible, the application rolls
back and the proposal remains pending.

### Approval rule

AI must never directly mutate shared Project State.

The flow is:

1.  AI produces a proposal.
2.  The backend stores it as pending.
3.  The executor reviews the proposal and its evidence.
4.  The executor accepts, rejects, or edits it.
5.  On acceptance, the backend validates and applies the change through
    the owning Project State service.
6.  The proposal is marked applied only after the state change succeeds.

Applying a proposal and changing Project State must occur in one
database transaction. Repeated application must not create duplicates.
An applied proposal remains idempotent on repeat requests. Invalid payloads,
changed evidence, or failed Project State service calls roll back both the
shared mutation and proposal review status.

## 7. Contradiction handling

AI may identify contradictory statements, such as two different
requirements expressed at different times.

AI must:

- preserve both source references;
- explain the detected inconsistency;
- create a private proposal for executor review;
- avoid deciding which statement is correct.

The executor decides how to resolve the contradiction. Once accepted,
the resulting conflict or requirement update becomes part of shared
Project State.

Questionnaire-to-passport conflicts are also preserved and presented for
executor review. They must not cause silent overwrites.

## 8. Triggering and background execution

AI operations run asynchronously through Celery when they may take
significant time.

For the MVP, analysis starts only when an active project executor manually
requests it. Questionnaire submissions, new messages, document processing,
and Project State changes do not trigger analyses. Chat batching/debounce is
not applicable while message-triggered analysis is disabled. A future
automatic trigger requires an explicit decision and documented batching
policy.

The API creates a durable `AIAnalysisRequest` before enqueueing Celery work and
returns its request UUID and status immediately. `Idempotency-Key` is scoped to
the project and executor, so retrying the same request returns the original
record. Requests move through queued, running, succeeded, or failed. Worker
claims use a six-minute lease and monotonically increasing generation; Celery
redelivery waits for an active lease, and expired leases can be reclaimed. A
stale worker cannot persist proposals after a newer generation claims the
request. Proposal creation and request completion commit together, preventing
duplicate visible proposals. Only stable error codes are stored; source text,
prompts, and provider exception detail are not logged.

## 9. Observability and cost control

Record per run:

- task key;
- provider and model actually used;
- profile/configuration version;
- prompt version;
- input hash;
- status and error code;
- execution timestamps;
- input/output token usage when available;
- estimated cost when available.

Do not store complete prompts or duplicate sensitive source content by
default. Store source IDs and evidence references.

### Specification generation source policy

Specification generation uses only the project passport and shared Project
State. The snapshot includes the passport and Project State stages,
requirements, tasks, open questions, and conflicts through their owning-app
selectors. It omits project name and description. Only confirmed, in-progress,
blocked, or completed requirements are approved commitments; draft
requirements are unconfirmed, and rejected requirements are excluded from the
current requirements list. Cancelled stages and tasks are excluded from the
current plan. An open question is labeled unresolved; an unresolved conflict is
explicitly labeled as a contradiction for which neither side is an
established fact. Dismissed questions and conflicts remain labeled dismissed
and are not requirements or decisions; a resolved conflict is represented
only by its recorded resolution. The generator must not choose a side or
invent missing facts. Chat, documents/RAG, internal AI analyses, and pending AI proposals
are excluded. This bounded policy avoids mixing unreviewed evidence into the
shared draft until the product defines an authority and disclosure policy
for those sources.

The asynchronous request stores the source-context SHA-256 hash and the
specification version only, not the complete prompt or a copy of source
content. A worker rebuilds the structured context and compares the hash
after building the prompt, immediately before calling the router, and again
before publishing. These checks use short transactions; no database lock is
held over the provider network call. If sources change before the call, the
request is superseded without sending stale input. If sources change during
the model call, its output is discarded. This provides source-change
detection without retaining a second copy of shared customer data. The router
applies the `specification_generation` profile's 32,000-byte input,
output-token, timeout, fallback, and cost limits; the specification worker
keeps its context below 24,000 UTF-8 bytes to leave room for the system prompt.

The request is committed before its initial Celery dispatch. A Beat sweep runs
every 60 seconds to recover queued requests older than one minute, including
the crash window between commit and the `on_commit` callback. Dispatch attempt
count and a two-minute dispatch lease are persisted under a row lock, and
recovery republishes the same request and Celery task IDs. Concurrent sweepers
cannot reserve the same dispatch simultaneously. After five attempts without
a worker claim, the request becomes terminal `failed` (`queue_unavailable`);
stale task copies then return without calling the provider. Worker claims still
use their own lease and generation fencing before any provider call.

Add timeouts, bounded retries, rate limits, and per-task cost
monitoring. Provider-specific errors must be normalized before reaching
business modules.

## 10. Questionnaire boundary

AI does not generate questionnaire definitions, questions, or branching
rules. Questionnaire schemas are authored and versioned by the product
team and validated deterministically by the backend.
