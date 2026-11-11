# ADR-005: REST, WebSocket, and OpenAPI Contract

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

Most ProjectBridge operations are ordinary resource reads and writes.
Chat requires real-time delivery. Frontend and backend need a shared
contract.

## Decision

- Use versioned REST API under `/api/v1/`.
- Use WebSocket under `/ws/v1/` for real-time chat delivery.
- Use REST for message persistence and history.
- Generate OpenAPI using drf-spectacular.
- Generate frontend TypeScript types from OpenAPI.

## Consequences

- API behavior is documented and type generation is reproducible.
- WebSocket is not the source of truth; persisted messages are
  recoverable through REST.
- Session authentication and project membership are checked for both
  REST and WebSocket.
- API versioning allows future incompatible changes without silently
  breaking clients.
