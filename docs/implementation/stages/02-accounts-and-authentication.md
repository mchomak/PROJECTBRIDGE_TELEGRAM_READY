# Stage 02 — Accounts and Authentication

**Goal:** Implement secure email-based accounts and browser
authentication.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Accounts
- `docs/api/API_CONTRACT.md` — Authentication endpoints
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`

## Dependencies

Stage 01.

## Scope

### Backend

- Create the custom Django user model before the first project
  migration.
- Use normalized, unique email as the login identifier.
- Use Django password hashing; configure Argon2 as the preferred hasher
  if compatible with the selected environment.
- Implement registration, login, logout, current-user,
  email-verification resend, and verification confirmation.
- Generate high-entropy verification tokens, store only token hashes,
  enforce expiration and single use.
- Use session authentication with HttpOnly cookies and CSRF protection.
- Configure local console email delivery.
- Add rate limiting or a clearly documented initial protection for
  registration and verification endpoints.
- Add common authentication and unauthenticated response handling.

### Frontend

- Build registration, login, email-verification, and
  authenticated-session states using FSD.
- Load the current user from the backend.
- Handle expired sessions and unauthenticated navigation.
- Do not store session credentials in local storage.

## Out of scope

- Social login or SSO.
- Multi-factor authentication.
- Password reset unless the product owner resolves the corresponding
  open decision.
- Account deletion/deactivation workflows.
- Project-specific roles; those arrive in Stage 03.

## Deliverables

- Custom user model and migrations.
- Authentication REST endpoints.
- Email verification flow.
- Session/CSRF configuration.
- Frontend auth screens and route guards.
- Tests for authentication and verification.

## Acceptance criteria

- [ ] A user can register with a valid email and password.
- [ ] Duplicate normalized emails are rejected.
- [ ] Passwords are stored only as secure hashes.
- [ ] A user can log in, retrieve their current profile, and log out.
- [ ] Email verification tokens expire and cannot be reused.
- [ ] Unverified accounts cannot be treated as email-verified.
- [ ] CSRF protection applies to state-changing browser requests.
- [ ] Session cookies are HttpOnly; production cookie settings are
  secure by default.
- [ ] Frontend does not store session tokens in local storage.
- [ ] Tests cover invalid credentials, duplicate emails, expired/reused
  tokens, and CSRF/session behavior.

## Stop conditions

If the existing repository already has a user model or migrations,
inspect them before changing `AUTH_USER_MODEL`. Do not replace an
established user model or rewrite migrations without a migration plan.

## Codex handoff

Implement Stage 02 only. Read the account, API, and security contracts
first. Do not add password reset or unrelated account features.
