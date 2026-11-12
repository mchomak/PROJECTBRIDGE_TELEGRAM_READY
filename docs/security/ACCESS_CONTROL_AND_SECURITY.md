# Access Control and Security

**Status:** Access model agreed; production compliance work remains  
**Last updated:** 2026-11-12

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

Starting a request and approving/rejecting it require both active project
roles and a parent project in `draft` or `active`. Only the other active
participant may approve or reject a request. Either active project
member may cancel a mutually approved deletion strictly before its
deadline, including after the parent project has completed or been
archived. Restoring an archived document is a separate action available
to either active member while the parent project is `draft` or `active`.
If a one-party deletion request is still pending, restoration cancels
that request and records the withdrawal; an approved deletion must be
explicitly cancelled before restoration.
An already approved deletion completes when due even if the parent
project later becomes completed or archived.

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

The completed/archived project read-only rule does not strand an already
approved document deletion: either active member may still cancel before
its deadline, and the scheduled sweep completes an uncancelled deletion
once due. This exception does not permit new lifecycle requests,
decisions, or document restoration in a completed/archived project.

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
- Generate tokens with `secrets.token_urlsafe(32)` and store only their
  SHA-256 hashes.
- Send the raw token only in the outbound email link fragment; never
  include it in API responses, database fields, application logs, or
  audit metadata.
- Expire invitations after seven days and allow revocation of pending
  invitations by the active project executor.
- Require the authenticated user’s verified email to match the invited
  email.
- Use shared Redis-backed limits: creation 20/hour/executor, preview
  30/hour/IP, and acceptance 10/hour/user.
- Do not reveal unnecessary project information before the invitation is
  validated.
- Public preview returns only the project name, a masked invited-email
  hint, expiry, and invitation status. Unknown tokens use a generic
  `404`; expired/revoked links use `410`; completed/archived projects use
  distinct `409` states. Email mismatch and unverified accounts return
  `403` without echoing the full invited address.
- The browser reads the raw token from the email-link fragment, removes
  the fragment before making API requests, and sends the token only in
  preview/acceptance POST bodies. Keep it in page memory only; do not put
  it in query parameters, local storage, session storage, API responses,
  database fields, or logs. Persist only its SHA-256 hash server-side.

## 6. API and WebSocket authorization

Every project-scoped REST endpoint must verify active project membership
and the required role.

Every project-scoped chat WebSocket connection must independently verify:

- browser `Origin` matches `FRONTEND_BASE_URL` or a configured
  `CSRF_TRUSTED_ORIGINS` entry; requests with a missing or foreign origin
  are rejected;
- authenticated session;
- active membership in the requested project;
- permission to subscribe to the requested event stream.

Never trust a project ID supplied by the client without checking
membership.

The originless `/ws/v1/health/` probe is a separate service check and is
not routed through the project chat authentication or origin validator.

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

- Enforce the `20 * 1024 * 1024` byte limit server-side.
- Validate the supported extension against detected file content;
  browser-provided MIME is not trusted.
- Generate UUID-based internal storage keys; the supplied filename is
  display metadata only and is never a filesystem path.
- Store files outside the public frontend directory.
- Authorize every download for an active member of the document's
  project and stream it through the backend as an attachment.
- Do not expose a public file URL or the internal storage key.
- Return `X-Content-Type-Options: nosniff` on file downloads.
- Apply processing time and resource limits to parsers.
- Treat document contents as untrusted input, including prompt-injection
  content.
- Malware scanning is not available in the MVP environment. Selecting
  and deploying a scanner is a production gate before public launch.

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
- A document may be permanently deleted only after both project
  participants approve deletion of that archived document. The fixed
  30-day cancellation period begins at the second approval. This
  document-level action does not automatically delete the project or
  any other project data.
- The previously proposed 12-month project-retention and 14-day backup
  periods are not approved product requirements. They must not trigger
  project deletion or be presented as user-facing retention promises.
- No automatic project-data purge is implemented. Any future project
  retention period or backup-expiration schedule requires a separate
  documented decision.
- Operational AI logs should retain metadata rather than full prompts or
  source contents; the exact retention period must be finalized.
- Test database and file restoration periodically.

Mutually approved permanent document deletion removes live source and
Stage 08 data after the cancellation deadline. Encrypted backups may
retain deleted files until their applicable operational expiry; do not
promise a fixed backup period or immediate erasure from every backup.

## 11. Deferred production requirements

The MVP implementation defers:

- user consent and privacy-notice flows for personal-data processing;
- explicit disclosure of external AI providers and their processing
  terms.

These are not to be treated as permanently unnecessary. Review
applicable legal and provider requirements and resolve them before
onboarding real public customers.
