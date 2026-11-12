# Stage 04 — Email-Bound Project Invitations

**Goal:** Allow an executor to invite a customer securely by email and
add the customer to the correct project.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Invitations and membership
- `docs/api/API_CONTRACT.md` — Invitations
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md` — Invitation security

## Dependencies

Stages 02 and 03.

## Scope

### Backend

- Implement ProjectInvitation and migrations.
- Normalize invited email addresses consistently.
- Generate high-entropy invitation tokens and store only token hashes.
- Support expiration, revocation, preview, and acceptance.
- Generate the raw token at creation time and send it only in the
  invitation email link; never return it in an API response.
- Require the authenticated user’s verified email to match the invited
  email.
- Enforce one active customer membership per project.
- Make acceptance atomic and safe against duplicate submissions.
- When a customer accepts an invitation for a `draft` project, atomically
  add the customer membership and transition the project to `active`.
  Acceptance is limited to `draft` and `active` projects; completed and
  archived projects do not accept invitations.
- Create and revoke invitations only while the project is `draft` or
  `active`.
- Send invitation emails through the configured email backend; local
  development uses console email.
- Rate-limit public invitation preview/acceptance endpoints.
- Avoid disclosing project details before a token is validated.

### Frontend

- Executor invitation form.
- Invitation status/list view.
- Invitation landing/preview screen.
- Login/register path for invited customers.
- Acceptance confirmation and clear email-mismatch/expired/revoked
  states.
- Customer project entry after successful acceptance.

## Out of scope

- Invitations to additional roles.
- Team or organization accounts.
- Multi-customer projects.
- Third-party identity providers.

## Deliverables

- Invitation model and service layer.
- Invitation API endpoints.
- Email template or message body.
- Executor and customer invitation UI.
- Security and concurrency tests.

## Acceptance criteria

- [ ] Only an executor can create or revoke invitations for their
  project.
- [ ] An invitation is bound to one normalized email address.
- [ ] Only the authenticated user with the matching verified email can
  accept it.
- [ ] Expired and revoked invitations cannot be accepted.
- [ ] Raw invitation tokens are not stored in the database or logs.
- [ ] Repeated acceptance does not create duplicate memberships.
- [ ] A project cannot acquire a second active customer.
- [ ] Accepting an invitation for a `draft` project changes its status to
  `active` in the same transaction as customer membership creation.
- [ ] Accepting an invitation for an `active` project leaves its status
  `active`; invitations for `completed` or `archived` projects cannot be
  accepted.
- [ ] Invitations cannot be created or revoked for `completed` or
  `archived` projects.
- [ ] Invitation endpoints do not leak project information for invalid
  tokens.
- [ ] Local invitation delivery is testable through the console email
  backend.
- [ ] Tests cover email mismatch, expiry, revocation, replay, and
  duplicate acceptance.

## Stop conditions

If invitation expiry duration or email-verification behavior is not
configured in the technical documents, select no hidden policy. Propose
a default and ask for approval before hard-coding a product-facing
duration.

## Codex handoff

Implement Stage 04 only. Preserve the email-binding rule as a
backend-enforced security invariant.
