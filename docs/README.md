# ProjectBridge — Technical Documentation

**Status:** Architecture baseline for the MVP  
**Language:** English  
**Last updated:** 2026-11-13

## Purpose

This documentation set records the technical and product decisions
agreed for the ProjectBridge MVP. It is the shared reference for
implementation, code review, and future architecture changes.

The documents describe the agreed direction. Details that still require
product or technical decisions are listed in
[OPEN_DECISIONS.md](OPEN_DECISIONS.md); they must not be silently
invented during implementation.

## Documentation map

| Document                                                               | Purpose                                                                       |
|:-----------------------------------------------------------------------|:------------------------------------------------------------------------------|
| [MVP Scope](product/MVP_SCOPE.md)                                      | Product boundaries, roles, MVP capabilities, deferred scope                   |
| [System Architecture](architecture/SYSTEM_ARCHITECTURE.md)             | Overall architecture, technology stack, repository layout, runtime components |
| [Frontend Architecture](architecture/FRONTEND_ARCHITECTURE.md)         | React, TypeScript, Vite, Feature-Sliced Design, client data management        |
| [Backend Architecture](architecture/BACKEND_ARCHITECTURE.md)           | Django modular monolith, module boundaries, internal code structure           |
| [Database Model](database/DATA_MODEL.md)                               | Entities, fields, relationships, constraints, database conventions            |
| [API Contract](api/API_CONTRACT.md)                                    | REST endpoints, WebSocket, payload conventions, permissions, errors           |
| [AI Architecture](ai/AI_ARCHITECTURE.md)                               | Provider adapters, per-task model routing, RAG, proposals, AI execution       |
| [Access Control and Security](security/ACCESS_CONTROL_AND_SECURITY.md) | Roles, permissions, authentication, secrets, security baseline, retention     |
| [Document Lifecycle](documents/DOCUMENT_LIFECYCLE.md)                  | Upload, parsing, storage, shared visibility, archive and deletion workflow    |
| [Local Development](operations/LOCAL_DEVELOPMENT.md)                   | Docker Compose services, environment configuration, local workflows           |
| [MVP Verification Report](operations/MVP_VERIFICATION_REPORT.md)       | Stage 13 integration evidence, checks, and known limitations                   |
| [Open Decisions](OPEN_DECISIONS.md)                                    | Items that must be decided before or during implementation                    |
| [Architecture Decision Records](decisions/)                            | Short records explaining major architecture choices                           |

## Recommended reading order

1.  MVP Scope
2.  System Architecture
3.  Backend Architecture and Frontend Architecture
4.  Database Model
5.  API Contract
6.  AI Architecture
7.  Access Control and Security
8.  Document Lifecycle
9.  Local Development
10. Open Decisions

## Decision status

The documents distinguish three kinds of information:

- **Agreed** — explicitly accepted during product and architecture
  discussions.
- **Baseline recommendation** — a concrete implementation direction
  selected to make the MVP coherent; revisit only if implementation
  evidence requires it.
- **Open** — not yet specified sufficiently for implementation. See
  `OPEN_DECISIONS.md`.

## Core architecture summary

- One Git monorepo.
- Frontend: React, TypeScript, Vite, Feature-Sliced Design.
- Backend: Django and Django REST Framework, implemented as a modular
  monolith.
- Database: PostgreSQL, with pgvector for vector search.
- Background processing: Celery with Redis.
- Real-time communication: Django Channels and WebSocket.
- Local orchestration: Docker Compose.
- API: versioned REST API plus WebSocket events.
- API documentation: OpenAPI generated from the backend; TypeScript
  types generated for the frontend.
- AI: provider adapters and independent model profiles for individual AI
  tasks.

## Repository ownership

This documentation is intended to live in the project repository under
`docs/`. When implementation changes an agreed decision, update the
relevant document and add or amend an ADR. Do not leave implementation
and documentation describing different architectures.
