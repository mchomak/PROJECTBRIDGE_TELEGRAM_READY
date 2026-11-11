# Interfaces — Stage 02 Accounts and Authentication

## Границы, решённые в спецификации

| Модуль | Владеет | Выставляет | Прячет |
|---|---|---|---|
| `accounts` backend | User, email verification tokens, normalization, auth state transitions, mail creation | `register_user(email, password) -> User`; `authenticate_user(email, password) -> User \| None`; `resend_verification(email) -> None`; `confirm_verification(raw_token) -> User`
`api_exception_handler(exc, context) -> Response`
`csrf_failure(request, reason) -> HttpResponse` | Django model persistence, token digest lookup/rotation, transaction locks, email body creation |
| `accounts.api` | REST serializers, permissions, views and OpenAPI schemas | seven REST endpoints from `API_CONTRACT.md` §5 | request parsing and mapping to service errors |
| `common` API support | stable API error envelope and CSRF failure response | DRF exception handler and `csrf_failure(request, reason) -> HttpResponse` | error code mapping and request ID creation |
| `entities/user` frontend | authenticated profile shape and current-user query | `useCurrentUser()` / `User` profile type from generated OpenAPI types | query cache details |
| `features/auth` frontend | auth actions and CSRF-aware requests | `register`, `login`, `logout`, `resendVerification`, `confirmVerification` mutations | endpoint payload wiring and mutation state |
| `pages/auth` frontend | auth route composition and guards | login/register/verify/verification-required/app routes | forms and presentation details from lower layers |
| `shared/api` frontend | same-origin request and CSRF boundary | `apiRequest(path, init)` and generated API types | cookie parsing and CSRF bootstrap sequence |

**Test seams:** backend behavior is checked through REST/APIClient plus the accounts service public signatures for race-sensitive token behavior; frontend behavior is checked through page rendering and shared API boundary. Use Django email outbox and database transactions as test tools, not alternate production interfaces.

## Stack and project rules

- ProjectBridge is a Django modular monolith and React/Vite FSD frontend. Dependencies flow `app -> pages -> widgets -> features -> entities -> shared`.
- Runtime pins: Python 3.13.18, Django 5.2.19, Node 24.22.2, Vite 8.3.7; PostgreSQL 17, Redis 7.4.12. Keep pins and lockfiles committed.
- This stage changes authentication only. Do not add project membership/roles, invitations, password reset, MFA, SSO, or account deletion.
- Use services for account transitions and selectors for reads; views stay thin. Use `settings.AUTH_USER_MODEL` for future user relations; never import `auth.User` directly.
- Never expose raw verification tokens in API responses, logs, or database fields. The local console mail backend is the delivery path.
- The user explicitly asked to skip the Autopilot dashboard. Do not open, serve, or update it.
- `.env` is ignored and may contain secrets. Do not read or print secret values. Add names/defaults to `.env.example` only when needed.
- Add `argon2-cffi` only as the pinned dependency needed for the explicitly requested Argon2 hasher. No other new dependencies without a ticket-level reason.
- If implementation reveals the migration plan cannot work without rewriting existing migrations or moving user data, stop the ticket as `BLOCKED` and report evidence; do not reset the local database or volumes.

## Repository evidence and migration contract

- `apps.accounts` exists but had no user model or account migrations before Stage 02.
- The only ProjectBridge migration is `common.0001_enable_pgvector`; the local database has Django `auth` migrations applied and `auth.User` has zero rows.
- Keep all existing migrations and the `auth_user` table unchanged. Create `accounts.User` in `accounts.0001_initial`, set `AUTH_USER_MODEL`, and verify both an empty database and the current local database. Do not drop volumes or clear data.

## Commands

Run from the repository root:

```powershell
docker compose build backend frontend
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
docker compose exec frontend npm run build
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
```

Use a separately created disposable PostgreSQL database for the clean-database migration check and remove only that test database afterward. Verify OpenAPI after rebuilding the backend, then generate frontend declarations; never edit generated declarations manually.
## Из ticket 01 — provisional handoff

`register_user(email, password) -> User`
`authenticate_user(email, password) -> User | None`
`resend_verification(email) -> None`
`confirm_verification(raw_token) -> User`
`api_exception_handler(exc, context) -> Response`
`csrf_failure(request, reason) -> HttpResponse`
## From ticket 02 — session API

`GET /api/v1/auth/csrf/() -> {csrf_token}`
`POST /api/v1/auth/register/({email, password}) -> 201 UserSummary`
`POST /api/v1/auth/login/({email, password}) -> 200 UserSummary`
`POST /api/v1/auth/logout/() -> 204`
`GET /api/v1/auth/me/() -> UserSummary`
`UserSummary(id, email, first_name, last_name, email_verified, email_verified_at)`
`ErrorEnvelope(code, detail, errors, request_id)`
## From ticket 03 — verification API

`POST /api/v1/auth/email-verification/resend/({email?}) -> 202 {detail}`
`POST /api/v1/auth/email-verification/confirm/({token}) -> 200 {email_verified, email_verified_at}`
## From ticket 04 — frontend auth flows

`apiRequest(path, init)`
`apiJson<T>(path, init)`
`useCurrentUser()`
`useLogin()`
`useRegister()`
`useLogout()`
`useResendVerification()`
`useConfirmVerification()`
