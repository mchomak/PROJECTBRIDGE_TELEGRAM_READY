# Requirement manifest

Source: 2026-11-11-brief.md. Requirements may be removed only by the user.

| ID | Exact source phrase | Status | Basis | Location |
|---|---|---|---|---|
| R01 | AGENTS.md | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R02 | docs/architecture/SYSTEM_ARCHITECTURE.md | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R03 | docs/architecture/FRONTEND_ARCHITECTURE.md | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R04 | docs/architecture/BACKEND_ARCHITECTURE.md | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R05 | docs/operations/LOCAL_DEVELOPMENT.md | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R06 | docs/api/API_CONTRACT.md | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R07 | Stage 00 | done | Read first / Stage 00 prerequisite verified | Phase 2 |
| R08 | Initialize Django and Django REST Framework | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R09 | Configure ASGI as the application entry point | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R10 | planned Django app package structure without speculative business models | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R11 | Django Channels | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R12 | Celery and Redis broker integration | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R13 | minimal health endpoint | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R14 | drf-spectacular, OpenAPI schema, and development Swagger UI | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R15 | settings separation for local development and production-safe defaults | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R16 | PostgreSQL and pgvector extension availability | done | Verified by ticket tests, review, and commit | Ticket 01 ? b0adfbc |
| R17 | React, TypeScript, and Vite | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R18 | FSD layer directories: app, pages, widgets, features, entities, shared | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R19 | application routing and a minimal application shell | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R20 | shared API client boundary | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R21 | Vite proxying for /api/ and /ws/ | done | HTTP and WebSocket proxy behavior verified in the combined runtime | Ticket 03 |
| R22 | reproducible OpenAPI-to-TypeScript type generation command | done | Live schema generation produced a non-empty declaration in the combined runtime | Ticket 03 |
| R23 | Do not hand-write duplicate API types | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R24 | Docker Compose services for frontend, backend, PostgreSQL with pgvector, Redis, and Celery worker | done | All five Compose services became healthy; frontend host port was bound to loopback in Ticket 04 | Ticket 03, Ticket 04 |
| R25 | Add Celery Beat only if a scheduled task is already required; otherwise leave it documented for later | deferred | No scheduled task is required in Stage 01; document Beat for later | Spec § Out of Scope |
| R26 | health checks | done | Compose readiness checks passed for all five services | Ticket 03 |
| R27 | persistent named volumes for database and uploaded-file storage | done | Database and media markers survived ordinary down/up | Ticket 03 |
| R28 | Django console email for local development | done | Runtime setting confirmed as Django console backend | Ticket 03 |
| R29 | Document commands to start, stop, inspect logs, run migrations, and execute tests | done | Setup guide documents the required operations | Ticket 03 |
| R30 | User registration and business models are out of scope | deferred | Explicitly listed in the brief as out of scope | Spec § Out of Scope |
| R31 | Product screens beyond the minimal shell are out of scope | deferred | Explicitly listed in the brief as out of scope | Spec § Out of Scope |
| R32 | Project workflows or AI provider integrations are out of scope | deferred | Explicitly listed in the brief as out of scope | Spec § Out of Scope |
| R33 | Running Django ASGI application; Running React/Vite application | done | Combined frontend and Django ASGI stack became healthy | Ticket 03 |
| R34 | Working PostgreSQL and Redis services | done | All Compose services healthy and backend readiness confirmed | Ticket 03 |
| R35 | Working Celery worker connection | done | Non-eager task result received from the Compose worker | Ticket 03 |
| R36 | Working Channels ASGI configuration | done | WebSocket health route returned status and normal close via Vite | Ticket 03 |
| R37 | OpenAPI schema and interactive docs | done | Schema and docs returned HTTP 200 in the combined runtime | Ticket 03 |
| R38 | Generated TypeScript type workflow | done | Live schema generation produced a non-empty declaration in the combined runtime | Ticket 03 |
| R39 | Docker Compose and local setup documentation | done | Compose and local setup guide delivered | Ticket 03 |
| R40 | A clean local setup can start all required services using documented commands | done | All services became healthy from the documented localhost setup | Ticket 03, Ticket 04 |
| R41 | Frontend loads in the browser | done | Frontend returned HTTP 200 in the combined runtime | Ticket 03 |
| R42 | Backend health endpoint returns success | done | Backend readiness returned HTTP 200 in the combined runtime | Ticket 03 |
| R43 | Backend connects to PostgreSQL and Redis | done | Backend readiness confirmed PostgreSQL and Redis in the combined runtime | Ticket 03 |
| R44 | pgvector is available in the configured database | done | PostgreSQL catalog query returned the vector extension | Ticket 03 |
| R45 | Celery worker starts and receives a test task | done | Non-eager task result received from the Compose worker | Ticket 03 |
| R46 | ASGI application starts with HTTP and WebSocket routing configured | done | HTTP and WebSocket routes passed in the combined runtime | Ticket 03 |
| R47 | /api/schema/ and /api/docs/ are available in development | done | Schema and docs returned HTTP 200 in the combined runtime | Ticket 03 |
| R48 | Vite proxies /api/ and /ws/ correctly | done | HTTP and WebSocket proxy behavior verified in the combined runtime | Ticket 03 |
| R49 | Database data survives ordinary container restarts | done | Database and media markers survived ordinary down/up | Ticket 03 |
| R50 | No domain functionality is implemented prematurely | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R51 | Do not guess incompatible package versions or database images | done | Exact tested package and image pins are documented | Ticket 03 |
| R52 | If a version decision affects pgvector, Django, Channels, or Celery compatibility, verify compatibility and document the chosen versions | done | Compatibility decisions and image tags are documented and runtime-tested | Ticket 03 |
| R53 | Implement Stage 01 only | done | Verified by ticket tests, review, and commit | Ticket 02 ? c25b6a9 |
| R54 | Verify the complete local runtime from a clean setup and include exact startup, health-check, and test commands in the report | done | Complete runtime and exact commands verified; POSIX health/schema commands also passed against CRLF `.env`; host port 8000 required the documented 8001 override here | Ticket 03 |
