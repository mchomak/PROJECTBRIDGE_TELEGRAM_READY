# ProjectBridge System Architecture

**Status:** Agreed architecture baseline  
**Last updated:** 2026-11-11

## 1. Architectural decisions

| Area                | Decision                                |
|:--------------------|:----------------------------------------|
| Repository          | Monorepo                                |
| Frontend            | React + TypeScript + Vite               |
| Frontend structure  | Feature-Sliced Design                   |
| Backend             | Python + Django + Django REST Framework |
| Backend structure   | Modular monolith                        |
| Database            | PostgreSQL                              |
| Vector search       | pgvector                                |
| Background jobs     | Celery                                  |
| Broker/cache        | Redis                                   |
| Real-time transport | Django Channels over WebSocket          |
| Local orchestration | Docker Compose                          |
| API documentation   | OpenAPI via drf-spectacular             |
| Frontend API types  | Generated from OpenAPI                  |

## 2. High-level architecture

The system is one product with a separately structured frontend and
backend in one repository.

The frontend communicates with the backend through:

- versioned REST endpoints for reads and commands;
- WebSocket for real-time chat events.

The backend owns all business rules, authorization, validation,
persistence, and AI orchestration. The frontend is not a security
boundary and must not be trusted to enforce permissions.

The backend is a modular monolith. Its business domains are separate
Django applications with explicit ownership and internal service
interfaces. They run as one deployable backend application, with
separate runtime processes for HTTP/WebSocket handling and background
workers where required.

## 3. Runtime components

### Frontend

- Vite development server.
- React application.
- TypeScript.
- Feature-Sliced Design boundaries.
- TanStack Query for server state and request caching.
- Generated TypeScript API types.

### Backend

- Django.
- Django REST Framework.
- ASGI application for HTTP and WebSocket support.
- Django Channels for WebSocket routing and authentication.
- Celery workers for long-running tasks.
- Celery Beat when scheduled tasks are required.

### Infrastructure

- PostgreSQL with the pgvector extension.
- Redis for Celery broker and Channels layer.
- Local persistent volume for uploaded files.
- Docker Compose for local orchestration.

## 4. Repository layout

The agreed repository is a monorepo. The following is the baseline
structure; implementation may add files inside these boundaries without
changing the architecture.

``` text
projectbridge/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── pages/
│   │   ├── widgets/
│   │   ├── features/
│   │   ├── entities/
│   │   └── shared/
│   ├── public/
│   └── package.json
├── backend/
│   ├── config/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── projects/
│   │   ├── invitations/
│   │   ├── questionnaire/
│   │   ├── chat/
│   │   ├── documents/
│   │   ├── project_state/
│   │   ├── ai_assistant/
│   │   ├── specifications/
│   │   └── common/
│   ├── manage.py
│   └── pyproject.toml
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── database/
│   ├── api/
│   ├── ai/
│   ├── security/
│   ├── documents/
│   ├── operations/
│   └── decisions/
├── infra/
│   └── docker/
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## 5. Architectural boundaries

- Frontend and backend share one repository, not runtime code.
- Frontend API types are generated from the backend OpenAPI schema.
- Backend domain modules own their models and business rules.
- A module must not directly mutate another module’s models as a
  shortcut.
- Cross-module writes go through the owning module’s service interface.
- Cross-module reads use documented selectors or query interfaces.
- Avoid circular imports and circular domain dependencies.
- Infrastructure concerns must not be embedded in domain rules.

## 6. Scaling strategy

A monolith can be scaled horizontally. Multiple backend instances can
run behind a load balancer and use the same PostgreSQL and Redis
infrastructure.

Background workers can be scaled independently by queue and workload.
HTTP, WebSocket, and Celery processes may run separately without
becoming microservices.

Initial scaling options:

- add backend instances;
- add Celery workers;
- separate queues for AI and document processing;
- optimize PostgreSQL indexes and queries;
- introduce caching where measured;
- move file storage from local volume to S3-compatible object storage.

Do not introduce microservices based only on user count. Consider
extraction only when a domain has a measurable independent scaling,
reliability, deployment, security, or team-ownership requirement.

## 7. Reliability principles

- Database transactions protect multi-step business operations.
- Enqueue background work after the database transaction commits.
- Long-running AI and document operations must not block ordinary HTTP
  requests.
- Background tasks must be retry-safe and idempotent where practical.
- WebSocket is a delivery channel; persisted data remains recoverable
  through REST.
- The database is the source of truth for project state.
