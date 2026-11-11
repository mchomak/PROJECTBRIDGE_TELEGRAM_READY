# ProjectBridge AI Architecture

**Status:** Core design agreed; provider/model selection remains open  
**Last updated:** 2026-11-11

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

Fallback profiles must support the same required capability and
compatible input/output semantics. Do not silently fall back to an
unrelated model.

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

The exact chunking strategy, similarity threshold, top-k values,
reranking policy, and embedding model remain open.

### Embedding compatibility

Vectors from different embedding models or incompatible dimensions must
not be mixed in the same active search index.

Changing the embedding profile requires re-embedding documents and a
controlled index migration/rebuild. Keep the old index available until
the new index is ready if uninterrupted search is required.

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

Candidate triggers for the MVP:

- customer questionnaire submission;
- new messages, grouped/debounced to avoid one expensive analysis per
  message;
- successful document processing;
- manual analysis initiated by the executor.

The exact trigger policy, debounce interval, duplicate-analysis
prevention, and whether every Project State update triggers analysis
remain open.

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

Add timeouts, bounded retries, rate limits, and per-task cost
monitoring. Provider-specific errors must be normalized before reaching
business modules.

## 10. Questionnaire boundary

AI does not generate questionnaire definitions, questions, or branching
rules. Questionnaire schemas are authored and versioned by the product
team and validated deterministically by the backend.
