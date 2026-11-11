# ADR-006: Use Per-Task AI Provider and Model Routing

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

Different ProjectBridge AI functions have different cost, latency,
reasoning, embedding, and retrieval requirements. The product must be
able to change provider/model for one function without changing business
logic.

## Decision

Use a central AI Router, provider adapters, capability-specific
interfaces, and independent model profiles keyed by task.

## Consequences

- Domain modules call stable internal task interfaces.
- Provider SDKs remain isolated inside adapters.
- Generation, embeddings, and reranking are distinct capabilities.
- Model configuration can vary per task.
- Credentials remain outside the database and frontend.
- AI runs record the provider/model/configuration actually used.
- Embedding model changes require a controlled re-embedding/index
  migration.
- AI proposals require executor approval before changing Project State.
