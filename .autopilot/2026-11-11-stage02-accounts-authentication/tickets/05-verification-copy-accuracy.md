# 05 — Verification email status copy

**Requirements:** R22
**Blocked by:** 04
**Zone:** `frontend/src/pages/auth/`, `frontend/src/app/App.test.tsx`
**Wave:** 4
**Status:** done

## Outcome

The verification-required screen must not claim that an email was sent after login. Per spec §8, registration sends the verification email; login only establishes a session and returns the user. Keep the registration confirmation accurate, and make the post-login message explain how to continue without implying a new email was dispatched.

## Acceptance criteria

- [ ] After an unverified login, the user sees clear next steps without a claim that an email was just sent.
- [ ] Registration may still say that the verification email was sent.
- [ ] Existing resend behavior and generic account-enumeration-safe response remain unchanged.
- [ ] A frontend test distinguishes the post-login state from registration confirmation.
- [ ] Frontend format, lint, typecheck, test, and build pass.

## Scope

Change only the verification-required copy and the focused frontend test needed to prove the distinction. Do not add endpoints, account behavior, persistence, or other auth flows. Do not use or update the Autopilot dashboard.