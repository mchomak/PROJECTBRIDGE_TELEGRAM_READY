# ADR-001: Use a Monorepo

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

The team consists of three people who work on the product part-time.
Frontend, backend, and documentation change together during the MVP.
Separate repositories would add coordination and versioning overhead
without a current need for independent release cycles.

## Decision

Keep frontend, backend, infrastructure configuration, scripts, and
technical documentation in one Git repository.

## Consequences

- One place for issues, code review, and project history.
- Atomic changes can update backend, frontend, API schema, and docs
  together.
- Shared CI can validate the complete product.
- Frontend and backend remain separate applications with separate
  dependency management.
- Repository boundaries must remain clear; monorepo does not mean mixing
  frontend and backend code.
