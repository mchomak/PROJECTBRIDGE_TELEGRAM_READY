# 01 — Django runtime and API skeleton

**Requirements:** R08-R16, R33-R37, R42-R47, R50, R53
**Blocked by:** none
**Zone:** `backend/`
**Wave:** 1
**Status:** ready

## What must work

The Django modular monolith starts as an ASGI app with the planned empty app packages, production-safe settings, readiness and WebSocket probes, OpenAPI docs, pgvector availability, and a Celery worker task contract. Implement only the operational scaffold described in `spec.md` and `interfaces.md`.

## From the brief, verbatim

> “Initialize Django and Django REST Framework.”
> “Configure ASGI as the application entry point.”
> “Add a minimal health endpoint.”
> “Configure PostgreSQL and the pgvector extension availability.”
> “Working Celery worker connection.”

## Specification sections

Backend skeleton and package boundaries; Stories and acceptance; Operational failure behavior; ASGI and Channels; Test seams; Version and compatibility decisions.

## Acceptance criteria

- [ ] Exact pinned backend dependencies are recorded; Django/DRF, local/test/production settings, URL config, ASGI config, and Celery bootstrap import cleanly.
- [ ] All planned app packages from `interfaces.md` have an initializer and AppConfig, with no business models or endpoints; only the pgvector extension migration exists.
- [ ] `GET /api/v1/health/` returns sanitized JSON 200 when database and Redis are reachable and 503 for dependency failure.
- [ ] `/ws/v1/health/` accepts one connection, sends a JSON status and closes; ASGI routes both HTTP and WebSocket.
- [ ] Development `/api/schema/` and `/api/docs/` work and the generated schema includes the health operation; docs are disabled outside development.
- [ ] Celery has a repeat-safe runtime probe task and Redis broker/result configuration; eager tests cover task behavior.
- [ ] Local email uses console output; production rejects missing/local secret and missing allowed hosts, with DEBUG disabled by default.
- [ ] Unit/integration tests cover health success, DB/Redis failures, schema, ASGI routing, settings safety, and pgvector migration behavior. Backend lint/format commands pass.
