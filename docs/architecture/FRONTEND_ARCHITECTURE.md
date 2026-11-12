# Frontend Architecture

**Status:** Agreed architecture baseline  
**Last updated:** 2026-11-11

## 1. Stack

- React
- TypeScript
- Vite
- Feature-Sliced Design (FSD)
- TanStack Query for server state
- React state for local UI state
- Generated API types from OpenAPI

Redux or Zustand is not part of the initial baseline. Add a global
client-state library only when a concrete state-management requirement
justifies it.

## 2. Feature-Sliced Design layers

The frontend uses the following layers:

| Layer      | Responsibility                                                |
|:-----------|:--------------------------------------------------------------|
| `app`      | Application initialization, providers, routing, global styles |
| `pages`    | Route-level page composition                                  |
| `widgets`  | Large reusable page sections                                  |
| `features` | User actions and business interactions                        |
| `entities` | Domain entities and their UI/data representations             |
| `shared`   | Generic UI, API client, utilities, configuration              |

Dependencies must flow downward. Lower layers must not import from
higher layers. Avoid circular imports between slices.

Typical direction:

`pages -> widgets -> features -> entities -> shared`

A page composes widgets. A widget may compose features and entities. A
feature implements a user action using entities and shared
infrastructure.

## 3. API integration

- Use one shared API client.
- Use session cookies for authentication.
- Include CSRF tokens on state-changing requests.
- Use generated TypeScript types from the backend OpenAPI schema.
- Use TanStack Query for server-state fetching, caching, invalidation,
  and mutation lifecycle.
- Do not duplicate backend business rules in frontend code.
- Do not place provider API keys or other secrets in frontend code.

Generated types belong under the shared API area, for example
`shared/api/generated/`. Generated files must not be edited manually.

## 4. Authentication and local origin

The browser application uses Django session authentication. The browser
automatically sends the HttpOnly session cookie; frontend code does not
read or write session credentials in `localStorage`.

During local development, configure the Vite development server to proxy
`/api/` and `/ws/` to the backend. This keeps browser requests on one
origin and simplifies cookie and CSRF handling. The shared API client
uses same-origin credentials. Before each state-changing request, it
reads the CSRF cookie or requests `/api/v1/auth/csrf/` to establish CSRF
context, then sends the token in `X-CSRFToken`.

Production must use HTTPS and correctly configured secure cookies. The
CSRF cookie is readable by the browser client; the session cookie remains
HttpOnly.

Authentication pages use `/login`, `/register`, `/verify-email`, and
`/verification-required`. Email verification links carry their token in
the URL fragment; the verification page reads it once, removes it from
the address bar, and submits it through the API.

The protected `/app` route loads the current user from `/api/v1/auth/me/`.
A `401` clears the cached user and redirects to `/login`. Network and
server failures remain visible with a retry action rather than being
treated as logout. An authenticated but unverified user is redirected to
`/verification-required`; only verified users enter `/app`.

## 5. Server state and local state

Use TanStack Query for data owned by the backend:

- projects;
- passport;
- questionnaire;
- messages;
- documents;
- Project State;
- AI proposals;
- specification.

Use React component state for transient UI state such as open dialogs,
selected tabs, form input before submission, and local interaction
state.

Do not treat a frontend cache as the authoritative source of project
data.

## 6. Real-time chat

- REST is the source of truth: it loads cursor-paginated message history
  and submits messages. History is newest-first, uses stable
  `(created_at, id)` ordering, defaults to 50 rows, and caps pages at
  100.
- WebSocket receives new-message events.
- On reconnect, the client retrieves messages missed during
  disconnection through the REST API.
- The client must handle duplicate delivery safely using message
  identifiers.
- A failed send can be retried with the original `client_message_id`
  and unchanged content.
- WebSocket authorization is enforced by the backend.

## 7. Permission-aware interface

The frontend may hide or disable actions that the current role cannot
perform. This is a usability feature only.

The backend must independently enforce every permission. A user must not
gain access by manually calling an endpoint or modifying client-side
state.

## 8. UI and domain separation

- Generic UI components belong in `shared/ui`.
- Domain-specific components belong in `entities`.
- User actions belong in `features`.
- Large page sections belong in `widgets`.
- Route composition belongs in `pages`.
- API request logic must not be duplicated across components.

The exact screen inventory and visual design system remain product/UI
work items.
