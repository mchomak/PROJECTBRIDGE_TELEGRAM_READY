# 02 — React/Vite shell and API contract boundary

**Requirements:** R17-R23, R33, R38, R41, R48, R50, R53
**Blocked by:** 01
**Zone:** `frontend/`
**Wave:** 2
**Status:** done; committed as `c25b6a9`. Live schema generation and HTTP/WebSocket proxy delivery are verified in Ticket 03.

**Pinned frontend dependencies for this ticket:** React/React DOM 19.3.1; @types/react 19.3.0; @types/react-dom 19.3.0; @types/node 24.19.2; @tanstack/react-query 5.107.1; TypeScript 5.9.3; Vite 8.3.7; @vitejs/plugin-react 6.3.0; react-router 7.16.0; openapi-typescript 7.13.0; Biome 2.6.6; Vitest 4.1.12; React Testing Library 16.3.3; jsdom 31.0.0.

## What must work

The frontend starts as a small React application with the agreed FSD directories, a root shell and router, one shared API request boundary, Vite HTTP/WebSocket proxies, and generated OpenAPI types. Implement only the operational shell; no product screens or workflows.

## From the brief, verbatim

> “Initialize React, TypeScript, and Vite.”
> “Create the FSD layer directories: `app`, `pages`, `widgets`, `features`, `entities`, `shared`.”
> “Create a shared API client boundary.”
> “Establish a reproducible OpenAPI-to-TypeScript type generation command.”
> “Do not hand-write duplicate API types.”

## Specification sections

Frontend skeleton; Frontend structure and contracts; Stories and acceptance; Test seams; Version and compatibility decisions.

## Acceptance criteria

- [ ] Exact package versions and committed lock file let `npm ci` install a Node-compatible app; Vite dev server and production build work.
- [ ] All six FSD directories exist under `src`; app initializes routing and global providers; `/` renders a minimal shell and unknown routes show a not-found state.
- [ ] No product screens, domain workflows, or manually duplicated API response types are introduced.
- [ ] `shared/api` exposes a single request function with same-origin credentials and CSRF cookie support for state-changing requests.
- [ ] Vite proxies `/api/` to backend HTTP and `/ws/` with upgrade support to backend ASGI.
- [ ] `npm run api:types` fetches the configured schema URL and generates the declaration under `shared/api/generated`; missing schema fails visibly and generated output is not hand-edited.
- [ ] Vitest/React Testing Library cover root shell, not-found route, and API boundary; format, lint, typecheck, and test commands pass.
