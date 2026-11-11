# Local Development and Operations

**Status:** Local runtime baseline  
**Last updated:** 2026-11-11

## 1. Goal

The MVP must run locally with persistent database storage and working
backend, frontend, chat, document processing, and AI integration
boundaries.

Docker Compose is the standard local orchestration mechanism.

## 2. Compose services

The baseline local environment contains:

| Service         | Purpose                                      |
|:----------------|:---------------------------------------------|
| `frontend`      | Vite development server                      |
| `backend`       | Django ASGI application, REST API, WebSocket |
| `postgres`      | PostgreSQL with pgvector extension           |
| `redis`         | Celery broker and Channels layer             |
| `celery-worker` | Background document and AI tasks             |
| `celery-beat`   | Scheduled jobs when required                 |
| file volume     | Persistent local document storage            |

The exact container images, versions, ports, and commands must be pinned
in the repository during implementation.

## 3. Browser origin and proxy

Configure Vite to proxy:

- `/api/` to Django;
- `/ws/` to the backend ASGI server.

This allows the browser to use one origin during local development and
simplifies session-cookie and CSRF behavior.

## 4. Environment variables

Commit `.env.example`, not `.env`.

Expected configuration categories:

- Django secret key and debug mode;
- database connection;
- Redis connection;
- allowed hosts and CSRF trusted origins;
- frontend base URL;
- local file-storage path;
- email backend;
- AI provider credentials;
- AI model/profile defaults.

Never commit real secrets. Never expose backend provider keys to Vite or
browser bundles.

## 5. Local email

Use Django’s console email backend for local development. Verification
and invitation emails are written to the backend console so developers
can retrieve the local links without a production mail service.

A real email provider is configured separately for deployed
environments.

## 6. Database setup

- Use PostgreSQL with pgvector available.
- Enable the required PostgreSQL extensions through migrations or
  documented database initialization.
- Run Django migrations from the backend.
- Use persistent volumes so database data survives container restarts.
- Do not rely on SQLite as a substitute for the production database
  model.

## 7. API documentation and types

Expose the generated OpenAPI schema and interactive API documentation in
development.

Generate frontend TypeScript API types from the OpenAPI schema. The
generation process should be reproducible and documented in package
scripts or repository scripts.

Generated types are not edited manually.

## 8. Background tasks

Run Celery workers separately from the HTTP server. Use dedicated queues
when workload separation becomes useful, especially for document
processing and AI tasks.

Scheduled cleanup, invitation expiry, and delayed document deletion may
require Celery Beat or another scheduler.

Tasks must be retry-safe and must not assume that a task is delivered
exactly once.

## 9. Development quality gates

Before merging a change:

- run backend tests;
- run frontend type checking;
- run frontend tests where present;
- run linting/formatting checks;
- verify migrations;
- regenerate OpenAPI and TypeScript types when API contracts change;
- update relevant documentation and ADRs.

Add tests for role permissions, cross-project access, questionnaire
conflicts, document lifecycle approvals, AI proposal application, and
WebSocket membership checks.

## 10. Local persistence and reset behavior

Database and uploaded files must use named Docker volumes or documented
local paths. A normal container restart must not delete user data.

Destructive reset commands must be clearly named and documented. Do not
make routine startup commands remove volumes.
