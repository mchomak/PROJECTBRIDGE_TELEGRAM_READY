# ADR-002: Use a Modular Monolith for the Backend

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

ProjectBridge has tightly related domains and frequent cross-domain
workflows. The team is small and part-time. Microservices would
introduce network contracts, distributed failure handling, independent
deployments, and eventual-consistency concerns before those costs
provide sufficient value.

## Decision

Implement one Django backend as a modular monolith. Use separate Django
apps for business domains and explicit internal service interfaces.

## Consequences

- One backend codebase and primary PostgreSQL database.
- Domain modules own their models and business rules.
- Cross-module writes go through the owning module’s services.
- HTTP, WebSocket, and Celery processes can run separately.
- Multiple backend instances and worker pools can scale horizontally.
- A domain may be extracted into a service later if measured
  requirements justify it.
- Microservices are not a target architecture requirement for the MVP.
