# ADR-016: AI Provider Routing and Task Profiles

**Status:** Accepted for the local MVP
**Date:** 2026-11-13; provider selection updated 2026-11-15

## Context

ProjectBridge needs a provider-neutral boundary for text generation,
embeddings, and reranking, with independent configuration per task. The
provider, model, fallback, timeout, retry, cost-control, and prompt-version
decisions were open before Stage 10.

## Decision

Use the official OpenAI Python SDK (`openai==3.49.0`) behind adapters
inside `apps.ai_assistant`. Domain code calls typed router operations by
task key. OpenAI calls use the Responses API for text generation and the
Embeddings API for vectors. DeepSeek uses the SDK against its compatible
Responses API for text generation and reranking.

Seed these independent profiles:

| Task | Default profile | Compatible fallback |
|---|---|---|
| `message_analysis` | `deepseek-flash` | none |
| `conversation_analysis` | `deepseek-flash` | none |
| `contradiction_detection` | `deepseek-flash` | none |
| `document_embedding` | `text-embedding-3-small`, 1536 dimensions | none |
| `rag_reranking` | `deepseek-flash` | none |
| `specification_generation` | `deepseek-flash` | none |

DeepSeek Flash supports the Responses API and JSON Schema output required
for the current generation and reranking contracts. It is selected as a
low-cost local integration model; quality is not the current test objective.
Its published peak rates are used in profile estimates: USD 0.30 per million
input tokens and USD 1.20 per million output tokens. The local profiles do
not configure a fallback; transient errors receive the router's one bounded
retry. OpenAI remains configured for embeddings only.

Profiles are configured in the backend-only Django Admin. `OPENAI_API_KEY`
and `DEEPSEEK_API_KEY` are read from backend/worker environment only and are
never stored in a profile row. `DEEPSEEK_BASE_URL` defaults to
`https://api.deepseek.com`. A missing key fails explicitly. No provider API
is called in tests.

Fallbacks share the task and capability. Text profiles share the typed
text/optional JSON-schema contract. Embedding fallback is rejected unless
provider, exact model identifier, dimensions, and embedding-space version
are identical. Retry transient rate limit, network, timeout, or server
failures once, then reserve fallback budget before making a compatible
fallback call. Before every provider attempt, reserve its maximum estimated
cost under a PostgreSQL task-scoped transaction lock shared by all profiles
for that task. Request and daily caps are frozen from the initial profile
for the entire call chain; a fallback may lower the effective request cap
but cannot raise either cap. Reservations accumulate across primary,
retry, and fallback attempts, and failures never release a reservation.
Reported token usage may raise the accumulated estimate when it exceeds the
latest attempt reservation; missing usage never lowers it.
An in-flight attempt uses the profile snapshot selected when that call chain
was routed; reservation prices, limits, model settings, and the adapter use
the same snapshot. Admin changes apply to later calls.
Do not fallback for missing credentials, authentication/permission
failure, invalid requests, or an unavailable model. Disable the SDK's
automatic retries so this bound is explicit. Request timeouts are profile
settings, seeded between 30 and 60 seconds.

Seed per-task daily reservations of USD 1.00, a USD 0.25 request ceiling
for generation and reranking, and USD 0.10 for embedding. Profiles also
cap input bytes, rerank candidates, output tokens, and timeouts. Reserve
the estimated maximum before each primary, retry, and fallback call and
reconcile with actual token usage afterward. Rates are editable profile snapshots
based on the linked provider pricing page; estimated cost does not cap
charges or costs outside ProjectBridge.

The caller supplies a prompt version label. Persist task, provider/model,
profile version, prompt version, SHA-256 input hash, status, timestamps,
attempt count, token usage, and estimated cost. Do not store prompts or
source text. `AIAnalysisRun` is project-scoped and visible only to backend
staff.

Use Responses structured output for reranking. The adapter requests one
score per candidate and the router rejects duplicate/missing indexes,
invalid scores, and malformed responses. This capability is available by
task key but is not automatically invoked by Stage 09 document retrieval.

For embeddings, derive `EmbeddingBatch.profile_key` from provider, exact
model identifier, and dimensions. `EmbeddingBatch.profile_version` is the
independent `embedding_space_version`, not `AIModelProfile.config_version`.
Changing timeout, cost rates, or fallback does not hide vectors. A model
change produces a different key; bump the space version if vector semantics
change behind an unchanged model identifier. The current document processor
does not support shadow slices or atomic cutover. Model changes require a
maintenance window: pause retrieval, switch the active profile, and run
`python manage.py reindex_document_embeddings --project-id <uuid>` (or
`--all-projects`). The documents-owned service queues a retry-safe task for
each active or archived document; lifecycle-pending, deleted, and
unsupported documents are excluded. Reprocessing replaces derived chunks
and embeddings without changing source files or confirmed project data.
Verify all eligible documents are ready with the new tuple before resuming
retrieval. Dimension changes require a shadow vector column/table migration.

The OpenAI Embeddings API allows 2,048 inputs per request, 8,192 tokens per
input, and 300,000 total input tokens per request. Bound each API call by
both the item count and the lower of the profile byte limit and a
200,000-byte UTF-8 safety ceiling; reject any individual input over 8,192
bytes. This uses UTF-8 bytes as a conservative token upper bound and leaves
headroom below the provider request ceiling. Gather every sub-batch before
the atomic document write and reject any change to the returned
`(profile_key, profile_version, model_name)` tuple.

## Consequences

- Each domain service can change its task profile without provider code.
- Embeddings remain in the Stage 09 model's 1536-dimensional vector
  space and carry a vector-space version independent of routing config.
- Live provider calls work only when the backend environment has a valid
  key and the account can use the configured model.
- External-AI privacy notice and data-processing review remain required
  before public onboarding, per `docs/security/ACCESS_CONTROL_AND_SECURITY.md`.
- Recheck provider availability and rate snapshots when changing profiles.

## Primary sources checked 2026-11-13 and 2026-11-15

- [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek Responses API](https://api-docs.deepseek.com/api/create-response/)
- [DeepSeek Responses API guide](https://api-docs.deepseek.com/guides/responses_api/)
- [DeepSeek JSON Output guide](https://api-docs.deepseek.com/guides/json_mode/)
- [OpenAI text-embedding-3-small model page](https://developers.openai.com/api/docs/models/text-embedding-3-small)
- [OpenAI Embeddings API request limits](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
- [OpenAI text embedding guide](https://developers.openai.com/api/docs/guides/embeddings)
- [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- [OpenAI model deprecations](https://developers.openai.com/api/docs/deprecations)
- [OpenAI Python SDK releases](https://github.com/openai/openai-python/releases)
