# ADR-015: Document Text Processing and Vector Search

- **Status:** Accepted
- **Date:** 2026-11-13
- **Decision owners:** Project owner

## Context

Project documents need searchable evidence while remaining shared data
under the existing mutual-consent lifecycle. The parser, chunking,
embedding, and retrieval settings were open. Provider credentials are not
available to the local MVP and must never be represented by mock vectors
as completed search processing.

## Decision

- Process uploads asynchronously through Celery after the upload
  transaction commits. Use pypdf 5.4.0, python-docx 1.1.2, and
  BOM-detected UTF-8/UTF-16/UTF-32 decoding for supported text formats.
- Inspect the DOCX central directory before opening it; reject ZIP64,
  more than 10,000 entries, or directories larger than 2 MiB. Limit a
  DOCX archive to 50 MiB uncompressed, a PDF to 5000 pages, and extracted
  text to 2 million characters. Celery applies a 180-second soft and
  240-second hard task limit.
- Split text into 1000-character chunks with 150-character overlap.
  Keep PDF pages and DOCX paragraphs/table cells separate, and preserve
  page, paragraph, table, row, cell, and character locations in metadata.
- Use OpenAI `text-embedding-3-small` with 1536 dimensions for the
  initial `document_embedding` task profile. Store those vectors in
  pgvector with cosine HNSW indexing.
- Retrieve the five nearest chunks by cosine distance by default, with
  no score cutoff or reranking. Require active project membership and
  filter to the requested project, active documents, ready processing
  status, and the exact embedding profile/version/model tuple.
- A missing or failing embedding service leaves the document failed and
  unsearchable. Extracted chunks may remain for a later retry; they do
  not imply successful indexing. A scanned PDF without a text layer is
  `unsupported`; malformed supported files are `failed`.
- Persist the embedding profile version beside its key and model, and
  include it in retrieval filters and uniqueness constraints.
- Replacing a same-dimension embedding model uses a separate
  profile/version/model slice and a complete re-embedding before retrieval switches. A vector
  dimension change requires a shadow column or table, verified backfill,
  and explicit cutover. Never mix vector spaces in one search operation.
- Mutually approved permanent deletion removes document chunks and
  embeddings along with the stored source file.

## Consequences

- Local tests use deterministic fake embedding results only at the AI
  boundary. Local runtime without configured credentials reports failed
  processing and cannot return RAG evidence.
- The vector schema is initially fixed to 1536 dimensions; alternate
  dimensions require a planned data migration.
- External AI privacy disclosure and provider credentials remain
  production gates. No provider key is stored in the database or
  frontend.
