# Access Control and Security

**Status:** Access model agreed; production compliance work remains  
**Last updated:** 2026-11-11

## 1. Roles

Each project has two active roles:

- `executor`
- `customer`

Role is project-scoped. A user’s role in one project does not determine
their role in another project.

The backend is the security boundary. Frontend hiding or disabling
controls is not authorization.

## 2. Permission matrix

| Resource/action                   | Executor | Customer |
|:----------------------------------|:---------|:---------|
| Read project                      | Yes      | Yes      |
| Update project metadata           | Yes      | No       |
| Read passport                     | Yes      | Yes      |
| Edit passport directly            | Yes      | No       |
| Submit questionnaire              | No       | Yes      |
| Read questionnaire/submission     | Yes      | Yes      |
| Read chat                         | Yes      | Yes      |
| Send chat messages                | Yes      | Yes      |
| Read documents                    | Yes      | Yes      |
| Upload documents                  | Yes      | Yes      |
| Request document archive/deletion | Yes      | Yes      |
| Approve document archive/deletion | Yes      | Yes      |
| Restore archived document         | Yes      | Yes      |
| Read all Project State            | Yes      | Yes      |
| Create/update Project State       | Yes      | No       |
| Read AI analyses                  | Yes      | No       |
| Read AI proposals                 | Yes      | No       |
| Accept/reject/apply AI proposals  | Yes      | No       |
| Read specification                | Yes      | Yes      |
| Generate/edit specification       | Yes      | No       |
| Create/revoke invitations         | Yes      | No       |

Both participants must consent to document archiving and permanent
deletion. The initiating participant’s request records their approval;
the other participant must approve separately.

### Project status overrides

The role matrix above applies subject to these project lifecycle rules.
Memberships remain active through completion and project archival, so
both participants retain read access to existing project data.

| Project status | Access and allowed changes |
|:---------------|:--------------------------|
| `draft` | The executor is the only active member until invitation acceptance and can edit project metadata and passport. A valid customer invitation acceptance moves the project to `active`. |
| `active` | The role matrix applies. |
| `completed` | Both participants can read project data, including the passport, chat history, documents, and Project State. Passport/project edits, new chat messages, document mutations/uploads, Project State changes, and new questionnaire answers are blocked. The executor may reopen to `active` or archive. |
| `archived` | The project is omitted from the main project list and appears in the separate archive list. Both participants can read existing data; all data mutations are blocked except executor restoration to `status_before_archive`. |

Only the executor can directly request a project status transition. The
`draft`-to-`active` change is performed by the invitation service after
the invited customer accepts; clients cannot set `status` through a
project metadata update. Archiving preserves project records, active
memberships, and documents. It is not deletion.

## 3. Shared information

All documents are shared. There is no private-document feature or
`visibility` field for documents.

All Project State entities are visible to both participants. Only the
executor can modify structured Project State records.

AI analysis runs and AI proposals are private to the executor. They must
not be included in shared Project State aggregates or customer-facing
API responses.

## 4. Authentication

Use Django session authentication for the browser application.

Requirements:

- Use Django session authentication. The session cookie is HttpOnly and
  uses `SameSite=Lax`; production session and CSRF cookies are Secure.
- `GET /api/v1/auth/csrf/` establishes the readable CSRF cookie and returns
  a token. Browser clients send it in `X-CSRFToken` on state-changing
  requests. Anonymous registration and login are subject to the same CSRF
  requirement as authenticated writes.
- HTTPS in production.
- Email verification before invitation acceptance.
- Login may create a session before email verification so the user can
  continue verification. The profile continues to report the address as
  unverified until confirmation; product routes remain gated.
- Return the same `401` response for unknown email and wrong password.
  Never reveal whether an email has an account through authentication or
  verification responses.
- Rate-limit authentication and token endpoints using the shared runtime
  cache. Initial DRF scopes are `register` 5/hour, `login` 10/minute,
  `resend` 3/hour, and `confirm` 10/hour. These are starting values, not
  final limits for all API groups.
- Return API failures in the common JSON envelope with `code`, `detail`,
  `errors`, and UUID `request_id`; unauthenticated requests receive `401`,
  permission/CSRF failures receive `403`, and throttled requests receive
  `429`. CSRF failure details must not expose middleware internals.
- Password hashing through Django’s password hashers; Argon2 is the
  preferred configured hasher.

Do not place session tokens or provider API keys in browser local
storage.

## 5. Invitation security

- Invitations are bound to a normalized email address.
- Generate high-entropy random tokens.
- Store only token hashes.
- Return the raw invitation token only at creation time.
- Enforce expiration and revocation.
- Require the authenticated user’s verified email to match the invited
  email.
- Rate-limit preview and acceptance endpoints.
- Do not reveal unnecessary project information before the invitation is
  validated.

## 6. API and WebSocket authorization

Every project-scoped REST endpoint must verify active project membership
and the required role.

Every WebSocket connection must independently verify:

- authenticated session;
- active membership in the requested project;
- permission to subscribe to the requested event stream.

Never trust a project ID supplied by the client without checking
membership.

## 7. Secret management

Local development:

- Store secrets in an untracked `.env` file.
- Commit `.env.example` with variable names and placeholders only.
- Add `.env` and local secret files to `.gitignore`.

Production:

- Use the hosting platform’s secret manager or an equivalent dedicated
  secret store.
- Rotate credentials when exposed or when personnel access changes.
- Keep separate credentials for development, staging, and production.
- Never log secrets or return them through API responses.
- Never bundle backend credentials into frontend assets.

AI provider keys remain backend-only. Database model profiles store
provider identifiers and model settings, not raw credentials.

## 8. File security

- Enforce the 20 MB limit server-side.
- Validate extension and detected MIME type.
- Generate internal storage keys; never use the supplied filename as a
  filesystem path.
- Store files outside the public frontend directory.
- Authorize every download.
- Apply processing time and resource limits to parsers.
- Treat document contents as untrusted input, including prompt-injection
  content.
- Consider malware scanning before production launch.

Public URL import is not part of the MVP, so URL-fetch/SSRF
functionality must not be added as part of document upload.

## 9. Logging and audit

- Do not log passwords, session identifiers, raw tokens, API keys, or
  unnecessary document contents.
- Record security-relevant project actions in ProjectAuditLog.
- Keep operational logs separate from business audit records.
- Include request IDs for tracing.
- Do not expose stack traces or provider credentials to users.

## 10. Data retention baseline

- Completed and archived projects, including their documents, are not
  automatically deleted in the MVP. Project archival is reversible and
  does not delete data.
- The previously proposed 12-month project-retention and 14-day backup
  periods are not approved product requirements. They must not trigger
  project deletion or be presented as user-facing retention promises.
- No automatic project-data purge is implemented. Any future project
  retention period or backup-expiration schedule requires a separate
  documented decision.
- Operational AI logs should retain metadata rather than full prompts or
  source contents; the exact retention period must be finalized.
- Test database and file restoration periodically.

For mutually approved permanent document deletion, communicate the
backup-retention behavior once an operational backup schedule is
approved.

## 11. Deferred production requirements

The MVP implementation defers:

- user consent and privacy-notice flows for personal-data processing;
- explicit disclosure of external AI providers and their processing
  terms.

These are not to be treated as permanently unnecessary. Review
applicable legal and provider requirements and resolve them before
onboarding real public customers.
