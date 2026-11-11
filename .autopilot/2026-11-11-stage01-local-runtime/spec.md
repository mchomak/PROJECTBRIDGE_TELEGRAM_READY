# Specification: Stage 01 — Application Skeleton and Local Runtime

## Problem

The repository has a documented architecture but no runnable application. Stage 01 must establish the first local end-to-end runtime without implementing ProjectBridge workflows.

## Result

One Compose project starts a React/Vite development shell, a Django ASGI application, PostgreSQL with pgvector enabled, Redis, and one Celery worker. The shell serves on port 5173; Django serves HTTP and WebSocket on port 8000. Vite proxies /api/ and /ws/ to Django so browser traffic stays on one origin.

The backend exposes a readiness endpoint at /api/v1/health/, an infrastructure WebSocket probe at /ws/v1/health/, and development OpenAPI/Swagger at /api/schema/ and /api/docs/. The health and probe surfaces are operational checks, not product workflows.

## Stories and acceptance

| ID | Story | Acceptance |
|---|---|---|
| R08-R11 | As a developer, I can start an intentionally empty Django modular monolith. | Django, DRF, ASGI, config, and the planned apps load; there are no business models. The only Stage 01 migration enables pgvector. |
| R11, R36, R46 | As a developer, I can run HTTP and WebSocket through one Channels ASGI application. | HTTP health and the /ws/v1/health/ probe both work through Daphne; Channels uses Redis for its channel layer. |
| R12, R35, R45 | As a developer, I can confirm a Celery worker receives a task. | The worker consumes the runtime probe from Redis and returns its result through the Redis result backend. |
| R13, R42-R43 | As a developer, I can check backend readiness. | GET /api/v1/health/ returns 200 JSON when Django, PostgreSQL, and Redis are available; it returns 503 without exposing credentials or stack traces when a dependency is unavailable. |
| R14-R15, R37, R47 | As a developer, I can inspect the API contract in development. | drf-spectacular provides a schema and Swagger UI; schema includes the health operation and can be fetched by the type generator. |
| R16, R44 | As a developer, I can use the configured Postgres database with pgvector available. | The pinned image contains the vector extension and a Django migration enables it. Querying pg_extension shows vector after migrations. |
| R15 | As an operator, I can use local settings and production-safe defaults. | Local, test, and production settings are separate. Production defaults DEBUG off, requires an explicit secret key and allowed hosts, and rejects the local-only secret. |
| R17-R18 | As a developer, I can run the React, TypeScript, and Vite app with the expected FSD layers. | The app starts and builds with the pinned Node image and package lock; src contains app, pages, widgets, features, entities, and shared. |
| R19 | As a developer, I can find the initial app shell through routing. | The root route renders a minimal shell; unknown paths render a minimal not-found message; no product workflow is presented. |
| R20, R22-R23, R38 | As a developer, I can call the backend through one shared API boundary and generate contract types. | The boundary uses same-origin credentials and CSRF cookie handling for state-changing requests. The api:types command generates the schema declaration from /api/schema/; generated output is never hand-edited. |
| R21, R24, R26-R29, R48 | As a developer, I can bring up and operate the local stack. | Compose defines frontend, backend, PostgreSQL/pgvector, Redis, and celery-worker, with health checks and documented start, stop, logs, migration, and test commands. Vite proxies /api/ and /ws/. |
| R27, R49 | As a developer, I can restart containers without losing local data. | PostgreSQL and uploaded media use named volumes; docker compose down without -v followed by up retains their contents. |
| R28 | As a developer, I can inspect local email output. | Local Django settings use the console email backend. |
| R30-R32, R50, R53 | As a developer, I can keep this stage limited to infrastructure. | There are no user registration flows, business models, project workflows, AI provider integrations, or product screens beyond the minimal shell. |
| R33-R39 | As a developer, I can follow a clean setup guide to run every required service. | The guide documents versions, env setup, startup, health checks, migrations, test execution, logs, and stopping the Compose project. |
| R40-R49, R54 | As a developer, I can verify the required local runtime from a clean checkout. | The exact commands in the guide start the services; health checks pass; the Celery probe returns success; pgvector exists; API docs and Vite proxies respond; persistence survives an ordinary restart. |

### Operational failure behavior

- If PostgreSQL or Redis is unavailable, backend readiness reports 503 and a short dependency status. It does not return exception text or configuration values.
- Compose waits for healthy PostgreSQL and Redis before starting the backend. Worker startup waits for Redis and the backend image/configuration to be available.
- Failed startup remains visible through container status and logs; no automatic destructive recovery or volume removal is performed.
- The frontend shell remains usable as a static page if the API is unavailable. It does not claim that backend operations work.
- Type generation fails with a non-zero exit code when the schema endpoint is unavailable and prints the source URL in the command output.

### ASGI and Channels

- config.asgi is the ASGI entry point and composes Django HTTP with a WebSocket URL router.
- /ws/v1/health/ is a small connection probe. It accepts the connection, sends a JSON status message, and closes cleanly. It contains no chat or membership behavior.
- The Channels layer uses channels_redis with REDIS_URL. It does not establish product chat or membership rules in Stage 01.

### Frontend structure and contracts

- frontend/src contains app, pages, widgets, features, entities, and shared layers. The six layers exist as directories even when a layer has no Stage 01 feature.
- The app layer initializes routing, global providers, and the application shell. The root route displays the shell; unmatched paths display a short not-found state.
- TanStack Query is initialized at the app boundary for server state, but Stage 01 adds no product query or workflow.
- shared/api contains the one fetch boundary. It uses same-origin credentials, includes a CSRF cookie value for state-changing requests, and leaves generated API contracts in shared/api/generated.
- Vite proxies /api/ to the backend HTTP server and /ws/ to the backend WebSocket server. The WebSocket proxy enables upgrades.
- The package script api:types reads http://localhost:8000/api/schema/ and writes the OpenAPI-derived declaration file. Generation requires the backend to be running and fails visibly if it is not.
- No API response or endpoint types are duplicated by hand.

### Backend package boundaries

The backend is a modular monolith under backend/config and backend/apps. The planned Django packages are accounts, projects, invitations, questionnaire, chat, documents, project_state, ai_assistant, specifications, common, and health. Each package gets its app configuration and package initializer; no model, service, selector, serializer, or business endpoint is created without Stage 01 need. The pgvector extension migration is the only migration introduced in this stage.

- config owns settings selection, URL registration, ASGI composition, and Celery app bootstrap. It exposes config.asgi.application and config.celery_app.app; startup composition remains internal.
- apps.common owns only the pgvector extension migration and generic operational probe integration. It exposes no domain model or cross-app business service.
- apps.health owns readiness checks and its read-only HTTP response. Its check boundary reports PostgreSQL and Redis availability without returning internal connection details.
- Frontend app owns initialization and route composition. It exposes the root shell through the router and hides provider setup.
- Frontend shared/api owns the single fetch boundary and generated schema file. It exposes a request function and generated OpenAPI paths; it hides CSRF-cookie parsing and request defaults.
- Compose owns service wiring, dependency readiness, published local ports, and persistent volumes. Container internals are not used as APIs.

### Test seams

- Django health readiness checks are tested through the public check function, with database and Redis outcomes isolated in unit tests.
- The ASGI app is tested through Django’s HTTP client and Channels’ WebsocketCommunicator.
- The Celery task is tested locally in eager mode; the documented runtime probe command verifies actual worker delivery and result retrieval in Compose.
- The frontend shell and route behavior are tested with Vitest and React Testing Library.
- The Compose runtime is verified externally with the documented health and persistence commands.

### Local setup commands

The operations guide provides equivalent PowerShell and POSIX shell commands for copying .env.example to .env and starting the full stack with docker compose up --build -d. It documents docker compose ps, docker compose logs -f, docker compose exec backend python manage.py migrate, backend and frontend test commands, API health checks, the pgvector extension query, and the Celery runtime probe. Stopping uses docker compose down without -v so named data volumes remain.

The frontend quality commands are npm run format:check, npm run lint, npm run typecheck, and npm test. The backend quality commands are ruff format --check ., ruff check ., and python -m pytest. They are runnable from the documented backend/frontend working directories.

## Version and compatibility decisions

All dependency versions are exact and committed through requirements.txt and package-lock.json. Container tags are fixed rather than floating.

| Component | Selected version | Compatibility reason |
|---|---|---|
| Python | 3.13.18, python:3.13.18-slim-bookworm | Supported by Django 5.2, Channels/channels_redis, and Celery. |
| Django | 5.2.19 LTS | Current patch in the supported 5.2 LTS line; Python 3.13 is supported. |
| Django REST Framework / schema | djangorestframework 3.17.2; drf-spectacular 0.30.0 | DRF supports Django 5.2 and is within drf-spectacular 0.30 compatibility. |
| Channels / Daphne | channels 4.3.2; Daphne 4.2.1 | Channels 4.3 supports Django 5.2 and ASGI HTTP/WebSocket routing. |
| Redis channel layer | channels_redis 4.3.0 | Requires Channels 4.2.2 or later and supports Python 3.13. |
| Celery / Redis client | Celery 5.7.0; redis-py 6.4.0 | Celery supports Python 3.13 and Redis server 6.2 or later; its Redis transport requires redis-py 6.4.0 or later. |
| PostgreSQL / pgvector | pgvector/pgvector:0.8.7-pg17-bookworm; pgvector 0.5.1; psycopg[binary] 3.3.8 | Upstream publishes the exact image tag; pgvector-python provides Django's VectorExtension migration; psycopg supports Python 3.13. |
| Redis server | redis:7.4.12-alpine3.21 | Exact image tag exists; Redis 7.4 is an extended-support open-source line and is supported by redis-py 6.4.0. |
| Backend quality tools | pytest 9.2.0; pytest-django 4.14.0; Ruff 0.17.4 | pytest-django 4.14 supports Django 5.2 and Python 3.13; Ruff provides the documented formatter and linter. |
| Node | 24.22.2, node:24.22.2-alpine3.23 | Exact Node 24 image exists and satisfies Vite's Node requirement. |
| React / React DOM | 19.3.1 | Current stable React release line. |
| React typings | @types/react 19.3.0; @types/react-dom 19.3.0 | React DOM typings require matching React typings in the 19.3 line. |
| TanStack Query | @tanstack/react-query 5.107.1 | Official package accepts React 18 or 19; Stage 01 uses it only for the app-level provider. |
| TypeScript | 5.9.3 | Latest published 5.x release; required by openapi-typescript 7.13.0's `typescript: ^5.x` peer range and supports the pinned Node runtime. |
| Node typings | @types/node 24.19.2 | Types match the Node 24 runtime line used by the frontend toolchain. |
| Vite / React plugin | Vite 8.3.7; @vitejs/plugin-react 6.3.0 | Vite 8 supports Node 20.19+ or 22.12+; Node 24 satisfies this. |
| Router / schema generator | react-router 7.16.0; openapi-typescript 7.13.0 | Stable router line; generator supports OpenAPI 3.0/3.1 and Node 20+. |
| Formatting / lint / tests | @biomejs/biome 2.6.6; Vitest 4.1.12; React Testing Library 16.3.3; jsdom 31.0.0 | One formatter/linter and Vite-native tests; jsdom 31 supports Node 24.15+ and the pinned Node 24.22.2 image. Exact versions are pinned in package-lock.json. |

Celery Beat is not included because Stage 01 contains no scheduled task; the operations guide records that a scheduler can be added when a real scheduled task enters scope.

## Assumptions

- The health URL is /api/v1/health/ and checks both PostgreSQL and Redis because the acceptance criteria require these dependencies to be connected. This follows the API contract's versioned REST prefix.
- A /ws/v1/health/ route exists only to prove WebSocket routing and Vite proxying. It follows the API contract's WebSocket prefix and does not establish a ProjectBridge chat protocol.
- The target local workflow is Docker Compose. No host-based application server command is required; backend and frontend tests remain available through their pinned project tools.
- The initial schema has no business API endpoints. Its generated TypeScript output represents only the actual operational endpoint.

## Out of scope

| Requirements | Reason |
|---|---|
| R25 — Celery Beat | No scheduled task is required in this stage; document for later. |
| R30 — User registration and business models | Explicitly outside Stage 01. |
| R31 — Product screens beyond the minimal shell | Explicitly outside Stage 01. |
| R32 — Project workflows or AI provider integrations | Explicitly outside Stage 01. |

## Requirement coverage

| Requirement | Specification section |
|---|---|
| R01-R07 | Source documentation and prerequisite verified |
| R08-R10 | Backend package boundaries |
| R11, R36, R46 | ASGI and Channels |
| R12, R35, R45 | Celery integration and Test seams |
| R13, R42-R43 | Operational failure behavior |
| R14-R15, R37, R47 | Stories and acceptance; setup guide |
| R16, R44 | Backend package boundaries; Version and compatibility decisions; migrations |
| R17-R19 | Frontend structure and contracts |
| R20-R23, R38 | Frontend shared API and generated types |
| R24, R26-R29, R48 | Local runtime and setup guide |
| R25, R30-R32 | Out of scope |
| R33-R39 | Result, backend, frontend, and local runtime |
| R40-R50, R54 | Stories and acceptance; Test seams |
| R51-R52 | Version and compatibility decisions |
| R53 | §9, Out of Scope |
| R54 | Stories and acceptance; setup guide; Test seams |
