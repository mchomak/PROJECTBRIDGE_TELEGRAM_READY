# Stage 09 — Document Text Processing and RAG

**Goal:** Process supported project documents asynchronously and make
their extracted text retrievable as grounded evidence.

## Read first

- `AGENTS.md`
- `docs/documents/DOCUMENT_LIFECYCLE.md`
- `docs/database/DATA_MODEL.md` — DocumentChunk and DocumentEmbedding
- `docs/ai/AI_ARCHITECTURE.md` — RAG pipeline
- `docs/operations/LOCAL_DEVELOPMENT.md`
- `docs/OPEN_DECISIONS.md` items 11–14 and 26–27

## Dependencies

Stages 01 and 08.

## Required decisions before vector migrations

Choose the initial embedding model and its vector dimension before
creating a fixed-dimension pgvector column/index. Confirm chunking,
similarity metric, retrieval top-k, and reranking requirements before
claiming RAG is production-ready.

## Scope

### Document extraction

- Implement asynchronous processing through Celery.
- Enqueue processing only after the upload transaction commits.
- Support text extraction from PDF, DOCX, TXT, and Markdown.
- Do not add OCR. Scanned/image-only PDFs without an extractable text
  layer must become unsupported or failed according to the approved
  status policy.
- Enforce parser execution/resource limits.
- Store extracted text as DocumentChunk records with stable chunk
  ordering and source metadata.

### Embeddings and retrieval

- Implement an embedding capability interface consumed through the AI
  Router contract; do not call a provider SDK directly from the document
  app.
- Store embeddings in pgvector using the approved model and dimension.
- Track embedding profile/model version.
- Implement project-scoped retrieval and metadata filters.
- Exclude archived and deletion-pending documents immediately.
- Provide evidence references that identify document, chunk, and
  relevant location.
- Ensure document deletion removes derived text and embeddings as
  required by the lifecycle.

### Frontend

- Display queued, processing, ready, failed, and unsupported statuses.
- Make it clear when a document is not yet searchable.
- Do not imply that upload completion means RAG processing has
  completed.

## Out of scope

- OCR, image extraction, audio, or video.
- Cross-project retrieval.
- Retrieval from private documents.
- Provider-specific SDK calls inside domain modules.
- AI-generated project changes; those are Stage 11.

## Deliverables

- Parser adapters and extraction tasks.
- Chunking service.
- DocumentChunk and DocumentEmbedding persistence.
- Embedding integration through the AI capability interface.
- Project-scoped retrieval service.
- Evidence reference format.
- Processing and retrieval tests.

## Acceptance criteria

- [ ] Upload returns without waiting for parsing or embedding.
- [ ] Celery processes supported formats asynchronously.
- [ ] Extracted text is stored in stable chunks with source metadata.
- [ ] Unsupported/scanned files are reported with an explicit status.
- [ ] Embeddings use one compatible active vector space.
- [ ] Retrieval is scoped to the current project.
- [ ] Archived and deletion-pending documents are excluded from
  retrieval.
- [ ] Evidence points back to the originating document and chunk.
- [ ] Retrying a processing task does not create duplicate chunks or
  embeddings.
- [ ] Tests cover extraction, malformed files, retries, project
  isolation, and lifecycle filtering.

## Stop conditions

Stop before vector migrations if the embedding model/dimension is not
selected. Stop if parser limitations make the agreed file support
impossible; report options rather than silently narrowing support.

## Codex handoff

Implement Stage 09 only. Keep parsing, chunking, embedding, and
retrieval as separate responsibilities; all provider calls must go
through the AI capability boundary.
