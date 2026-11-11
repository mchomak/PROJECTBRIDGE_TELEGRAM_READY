# ADR-004: Use PostgreSQL as the Primary Database

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

ProjectBridge requires relational integrity across users, projects,
membership, questionnaires, messages, documents, Project State, AI
proposals, and audit records. RAG also requires vector storage.

## Decision

Use PostgreSQL as the primary database and pgvector for vector search.
Use UUID identifiers, relational foreign keys, database constraints,
JSONB only for genuinely variable structures, and explicit lifecycle
states.

## Consequences

- Business relationships and uniqueness rules are enforced by the
  database.
- Project State remains queryable relational data rather than one large
  JSON document.
- pgvector supports document retrieval.
- Embedding dimensions and index migration must be managed deliberately.
- PostgreSQL-specific features are part of the application baseline;
  SQLite is not a production substitute.
