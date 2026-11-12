# ADR-011: Invitation expiry and rate limits

**Status:** Accepted  
**Date:** 2026-11-12

## Context

Invitation expiry and rate limits were open implementation decisions.
The Stage 04 specification sets the invitation lifetime and per-scope
limits so the email-bound workflow can be implemented consistently.

## Decision

- Invitations expire seven days after creation.
- Generate invitation tokens with `secrets.token_urlsafe(32)`; persist
  only a unique SHA-256 hex digest.
- Treat the raw token as email-link-only: place it in the outbound link
  fragment, never in the API response, and never persist or log it. Store
  only its SHA-256 digest; audit metadata excludes it as well.
- Use the shared Redis cache with fixed UTC-hour buckets for these limits:
  - Creation: 20 requests per active executor.
  - Preview: 30 requests per client IP.
  - Acceptance: 10 requests per authenticated user.
- Invitation create and revoke operations are executor-only and require
  project status `draft` or `active`; invitation listing remains
  available to the executor in every project status.

## Consequences

Expired pending invitations are transitioned to `expired` when listed
or when the executor attempts to invite the same normalized address
again. A pending invitation remains unique per project and normalized
email. The project database constraint remains authoritative for the
single active customer membership. Exceeding a limit returns `429`.

The implementation uses Django's configured default cache; local
development and production settings point it at Redis. Test settings may
replace the cache with an in-memory backend.
