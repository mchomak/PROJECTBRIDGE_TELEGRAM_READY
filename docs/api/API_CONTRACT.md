# ProjectBridge API Contract

**Status:** Endpoint baseline; Stage 02 authentication schemas finalized;
other request/response schemas remain to be finalized  
**API version:** v1  
**Last updated:** 2026-11-12

## 1. Transport and conventions

- REST over HTTP for reads and commands.
- JSON request and response bodies unless an endpoint explicitly uses
  `multipart/form-data`.
- WebSocket for real-time chat delivery.
- Base REST prefix: `/api/v1/`.
- WebSocket prefix: `/ws/v1/`.
- Field names: `snake_case`.
- IDs: UUID strings.
- Timestamps: ISO 8601 UTC.
- Decimal values: decimal strings.
- Authentication: Django session cookies.
- CSRF protection: required for state-changing browser requests.

## 2. HTTP methods

| Method | Use                                                                                           |
|:-------|:----------------------------------------------------------------------------------------------|
| GET    | Read a resource or collection                                                                 |
| POST   | Create a resource or execute a business action                                                |
| PATCH  | Partially update a resource                                                                   |
| PUT    | Full replacement only where explicitly required                                               |
| DELETE | Avoid for protected business entities; use lifecycle actions where deletion requires workflow |

Use POST action endpoints for state transitions such as accepting an
invitation, approving document deletion, or applying an AI proposal.

## 3. Response and error conventions

Successful responses use standard HTTP status codes.

| Status | Meaning                                       |
|-------:|:----------------------------------------------|
|    200 | Successful read or update                     |
|    201 | Resource created                              |
|    202 | Asynchronous operation accepted               |
|    204 | Successful operation with no response body    |
|    400 | Validation or malformed request               |
|    401 | Authentication required or invalid            |
|    403 | Authenticated user lacks permission           |
|    404 | Resource does not exist or is not accessible  |
|    409 | State conflict or optimistic-locking conflict |
|    413 | Upload exceeds size limit                     |
|    415 | Unsupported media type                        |
|    429 | Rate limit exceeded                           |
|    500 | Unexpected server error                       |

Use one consistent error envelope with machine-readable `code`,
human-readable `detail`, optional field-level `errors`, and a
`request_id`. Do not expose stack traces, secrets, or internal provider
responses to clients.

## 4. Pagination

- Use page-number pagination for ordinary collections unless a
  collection requires cursor semantics.
- Use cursor pagination for chat history.
- Return a stable ordering for every paginated collection.
- Do not return unbounded project histories or document lists.

## 5. Authentication endpoints — `accounts`

| Method | Endpoint                                   | Permission                | Purpose                      |
|:-------|:-------------------------------------------|:--------------------------|:-----------------------------|
| GET    | `/api/v1/auth/csrf/`                       | Public                    | Set/return CSRF context      |
| POST   | `/api/v1/auth/register/`                   | Public                    | Register a user              |
| POST   | `/api/v1/auth/login/`                      | Public                    | Create authenticated session |
| POST   | `/api/v1/auth/logout/`                     | Authenticated             | End session                  |
| GET    | `/api/v1/auth/me/`                         | Authenticated             | Return current user          |
| POST   | `/api/v1/auth/email-verification/resend/`  | Public/authenticated flow | Resend verification          |
| POST   | `/api/v1/auth/email-verification/confirm/` | Public                    | Verify email using token     |

Unverified users must not accept email-bound project invitations.
Password reset is not yet specified and is listed as an open decision.

### Session authentication contract

`GET /api/v1/auth/csrf/` returns `{"csrf_token": "..."}` and sets the
readable CSRF cookie. Browser clients send that token in `X-CSRFToken` on
every state-changing request. This applies to anonymous registration and
login as well as authenticated requests.

Registration accepts `{"email": "...", "password": "..."}` and returns
`201` with a `UserSummary`; it sends the verification email and does not
create a session. Invalid credentials, a weak password, or an existing
normalized email return `400` with field-level `errors` where applicable.

Login accepts the same credentials and returns `200` with a `UserSummary`
and an HttpOnly Django session cookie. Unknown email and wrong password
both return the same `401` response. Unverified accounts may log in to
continue verification; `email_verified` remains `false` and
`email_verified_at` remains `null` until confirmation.

`GET /api/v1/auth/me/` returns only the current session's user profile:
`id`, normalized `email`, `first_name`, `last_name`, `email_verified`, and
`email_verified_at`. It returns `401` when the request has no valid session.
Authenticated `POST /api/v1/auth/logout/` invalidates the session and
returns an empty `204` response; it also requires CSRF validation.

API errors use the JSON envelope `{"code": "...", "detail": "...",
"errors": null, "request_id": "<uuid>"}`. `errors` contains field
details for validation failures. Authentication-required requests return
`401`; permission or CSRF failures return `403`; throttled requests return
`429`. Responses do not include stack traces, secrets, or internal error
details.

Initial DRF scoped authentication throttles use the configured shared
cache: `register` 5/hour, `login` 10/minute, `resend` 3/hour, and `confirm`
10/hour. Exceeding a scope returns `429` with the common error envelope.
These are starting limits; see open decision 21 for remaining endpoint
groups and final review.

## 6. Projects and passport — `projects`

| Method | Endpoint                                  | Permission                    | Purpose                                |
|:-------|:------------------------------------------|:------------------------------|:---------------------------------------|
| GET    | `/api/v1/projects/`                       | Authenticated                 | List member projects except archived projects |
| GET    | `/api/v1/projects/?status=archived`        | Authenticated                 | List archived member projects          |
| POST   | `/api/v1/projects/`                       | Authenticated, verified email | Create a `draft` project, executor membership, and passport |
| GET    | `/api/v1/projects/{project_id}/`          | Project member                | Read project                           |
| PATCH  | `/api/v1/projects/{project_id}/`          | Executor                      | Update project metadata                |
| GET    | `/api/v1/projects/{project_id}/members/`  | Project member                | List participants                      |
| POST   | `/api/v1/projects/{project_id}/complete/` | Executor                      | Complete project                       |
| POST   | `/api/v1/projects/{project_id}/reopen/`   | Executor                      | Reopen a completed project             |
| POST   | `/api/v1/projects/{project_id}/archive/`  | Executor                      | Archive project                        |
| POST   | `/api/v1/projects/{project_id}/restore/`  | Executor                      | Restore an archived project            |
| GET    | `/api/v1/projects/{project_id}/passport/` | Project member                | Read passport                          |
| PATCH  | `/api/v1/projects/{project_id}/passport/` | Executor                      | Update passport                        |

Project creation is atomic: create Project, executor ProjectMember, and
ProjectPassport in one database transaction.

The project lifecycle is:

- Creation sets `status=draft`.
- Accepting a valid customer invitation moves `draft` to `active` in the
  invitation-acceptance transaction. A customer cannot submit a status
  value directly.
- `complete/` accepts only `active` and moves it to `completed`.
- `reopen/` accepts only `completed` and moves it to `active`.
- `archive/` accepts `draft`, `active`, or `completed`; it saves the
  previous value in `status_before_archive` and moves the project to
  `archived`.
- `restore/` accepts only `archived`, restores `status_before_archive`,
  and clears that field.
- Invalid lifecycle transitions return `409 Conflict`. Only the
  executor may call the lifecycle action endpoints.

The default project list excludes archived projects. The
`?status=archived` filter supplies the separate archive list. Active
members may read projects, members, and passports in every status.
Metadata and passport updates are allowed only in `draft` and `active`.
`completed` projects are read-only except for executor reopen/archive
actions. `archived` projects are read-only except for executor restore.
Neither transition deletes the project or its documents.
`status_before_archive` is server-managed, is not accepted in client
payloads, and is not exposed as an editable API field.

## 7. Invitations — `invitations`

| Method | Endpoint                                                            | Permission                    | Purpose                                           |
|:-------|:--------------------------------------------------------------------|:------------------------------|:--------------------------------------------------|
| GET    | `/api/v1/projects/{project_id}/invitations/`                        | Executor                      | List invitations                                  |
| POST   | `/api/v1/projects/{project_id}/invitations/`                        | Executor                      | Create email-bound invitation                     |
| POST   | `/api/v1/projects/{project_id}/invitations/{invitation_id}/revoke/` | Executor                      | Revoke invitation                                 |
| POST   | `/api/v1/invitations/preview/`                                      | Public, rate-limited          | Validate token and return safe invitation details |
| POST   | `/api/v1/invitations/accept/`                                       | Authenticated, verified email | Accept invitation                                 |

Create accepts `{ "invited_email": "customer@example.com" }` and
returns the invitation id, project id, normalized email, status,
expiration, lifecycle timestamps, and creation time. The response never
contains the raw token or invitation link. List uses page-number
pagination with a default page size of 20 and a maximum of 100; an active
executor can list statuses in any project lifecycle state.

The invitation is bound to a normalized email address. The authenticated
user’s verified email must match it. The raw token is included only in the
outbound email link and is never returned by the API; only its hash is
stored. Creation and revocation require the
active executor and a `draft` or `active` project. Revocation applies to
pending invitations only. A duplicate active invitation, an existing
active customer, or a disallowed project status returns `409`. Invitation
creation is limited to 20 requests per executor per UTC hour through the
shared Redis cache and returns `429` when exceeded. The outbound email
link is `<FRONTEND_BASE_URL>/invite/#token=<raw-token>`; the fragment
keeps the token out of the HTTP request URL.

Invitations may be accepted only while a project is `draft` or `active`.
Accepting an invitation for a `draft` project atomically adds the customer
membership and moves the project to `active`.

Preview accepts `{ "token": "<raw-token>" }` and returns only
`project_name`, a masked `email_hint`, `expires_at`, and invitation
`status`; it does not return the project description or member list.
Acceptance accepts the same token body and returns
`{ "invitation_id": "<uuid>", "project_id": "<uuid>",
"status": "accepted" }`. The browser reads the token from the email-link
fragment, removes the fragment from the address bar, and sends the token
only in the preview and acceptance request bodies. It is not stored in
browser local or session storage.

The public preview is limited to 30 requests per client IP per UTC hour;
acceptance is limited to 10 requests per authenticated user per UTC hour
through the shared Redis cache. Unknown tokens return `404` with the
generic `not_found` code. Known expired and revoked invitations return
`410` with `invitation_expired` or `invitation_revoked`; a project that
is completed or archived returns `409` with `project_completed` or
`project_archived`. An unverified account or an account whose normalized
verified email does not match the invitation returns `403` with
`email_unverified` or `email_mismatch`. Exceeding a limit returns `429`
with the common error envelope. These failures do not include the full
invited email or project details for unknown tokens.

Acceptance requires a verified account whose normalized email matches
the invitation. The customer membership, `draft`-to-`active` transition,
accepted invitation state, and their audit records commit in one
transaction. An already-active project stays active. Repeating an
acceptance by the user who accepted it returns the same result without a
duplicate membership or audit record; a second active customer returns
`409` without partial changes.

## 8. Questionnaire — `questionnaire`

| Method | Endpoint                                                                | Permission                    | Purpose                                      |
|:-------|:------------------------------------------------------------------------|:------------------------------|:---------------------------------------------|
| GET    | `/api/v1/projects/{project_id}/questionnaire/`                          | Project member                | Get applicable schema and current submission |
| POST   | `/api/v1/projects/{project_id}/questionnaire/submissions/`              | Customer                      | Start a submission                           |
| PATCH  | `/api/v1/questionnaire/submissions/{submission_id}/answers/`            | Customer, editable state only | Save answers                                 |
| POST   | `/api/v1/questionnaire/submissions/{submission_id}/refresh-passport-version/` | Customer, draft only          | Refresh a stale draft's concurrency version |
| POST   | `/api/v1/questionnaire/submissions/{submission_id}/submit/`             | Customer, draft only           | Validate, map, and lock the submission      |
| POST   | `/api/v1/questionnaire/submissions/{submission_id}/request-correction/` | Executor, submitted state only | Create a superseding correction draft        |
| GET    | `/api/v1/projects/{project_id}/questionnaire/conflicts/`                | Executor                       | List unresolved questionnaire conflicts     |
| POST   | `/api/v1/questionnaire/conflicts/{conflict_id}/resolve/`                | Executor                       | Keep the passport value or apply the answer  |

Reads require an authenticated active project member and return `404`
for projects the caller cannot access. Draft mutations and submission
require the active project customer, an `active` project, and CSRF. An
executor or caller from another project cannot edit or submit the draft.
Starting a draft accepts an empty JSON object, returns `201` when created
and `200` when an existing draft is resumed. Saving accepts
`{ "answers": { "<question_key>": <JSON value> } }` and returns the
submission with its current answer origins. Draft saves are partial
updates, validate each supplied answer and branch on the backend, and
return `400` for unknown, invalid, or inactive-branch answers. A
non-active project or non-draft submission returns `409`.

The GET response contains the applicable schema key, project type,
version, product-authored questions, the current submission, and
submission `history` ordered newest first. The current submission is the
editable draft when one exists; otherwise it is the latest immutable
submission. New drafts select the latest version for the project type;
correction drafts stay pinned to their source schema version. The backend
is authoritative for required fields, types, cross-field validation, and
deterministic branching.

`refresh-passport-version/` accepts an empty JSON object and returns the
draft with its current passport version. It is available to the draft's
customer after a stale-version response. It changes only the draft's
concurrency token; answers, origins, confirmation state, and passport are
unchanged. The customer can review the preserved draft and submit again.

Submit accepts `{ "confirm_prefilled": true|false }`. A complete draft
with unconfirmed passport-prefilled answers requires explicit
`confirm_prefilled: true`; otherwise the API returns `400` and leaves the
draft editable. Successful submission records the actor and time, locks
the submitted answers, and returns the immutable version. It compares
the passport version captured by the draft; a stale version returns `409`
with code `conflict` and atomically leaves the submission,
answers, and passport unchanged. The customer can explicitly refresh the
draft version before retrying.

On submission, the questionnaire service sends only explicit mappings
through the projects-owned, versioned
`projects.services.apply_questionnaire_mapping` service. Empty optional
answers do not clear the passport. Empty target fields are populated,
equal values are no-ops, and differing non-empty values are preserved in
an executor-only questionnaire conflict queue. The queue returns stored
passport/answer snapshots and is not exposed to customers or shared
Project State.

Conflict resolution accepts
`{ "decision": "keep_passport"|"apply_answer",
"expected_passport_version": <positive integer> }`. The executor's
decision is checked against the current passport version and affected
field snapshot. `apply_answer` uses the projects passport update service;
`keep_passport` leaves the passport untouched. Both decisions record an
actor and safe audit metadata without answer contents.

An executor correction request changes the submitted source status to
`correction_requested` without altering its answers, then returns one
new editable draft with copied answers and the same schema version. The
draft points to its source through `supersedes_id`; repeating the request
returns that draft. The submission history retains the source and each
correction version.

## 9. Chat — `chat`

| Method | Endpoint                                  | Permission     | Purpose                        |
|:-------|:------------------------------------------|:---------------|:-------------------------------|
| GET    | `/api/v1/projects/{project_id}/messages/` | Active member | Read paginated message history |
| POST   | `/api/v1/projects/{project_id}/messages/` | Active member | Submit a message               |

Message history is available to both active project roles in every
project status. It is ordered newest first by `(created_at, id)` and
uses signed cursors in the `next` and `previous` response links. The
`page_size` query parameter defaults to 50 and is capped at 100. The
response contains `next`, `previous`, and `results`; each result includes
`id`, `project_id`, `sender_id`, `content`, `message_type`,
`client_message_id`, `created_at`, and `updated_at`.

POST accepts `client_message_id` (UUID) and non-blank `content` (up to
10,000 characters after trimming outer whitespace). Sending is allowed
only while the project is active. A new message returns `201`; retrying
the same ID and normalized content returns the original message with
`200`, while reusing that ID with different content returns `409`.
New REST sends are limited to 60 per user per fixed UTC minute via a
shared Redis counter; exceeding the limit returns `429`. The limiter is
user-scoped and idempotent replays do not count as new sends. Audit
metadata records the actor role and message identifier, never message
content.

WebSocket:

`/ws/v1/projects/{project_id}/chat/`

The WebSocket connection uses the authenticated session and must verify
active project membership. It joins only the matching project group.
REST owns persistence, history, and message submission; the WebSocket is
delivery-only and does not accept client message commands. A newly
committed message is broadcast to that project group in an envelope with
`type: "message.created"` and a `message` property containing the
`MessageResponse` fields above. Publication happens after the database
transaction commits, and an idempotent REST replay does not publish
another event. After connecting or reconnecting, clients retrieve the
latest history through REST and deduplicate live events by `message.id`.

REST remains the source of truth for messages. WebSocket delivery is
implemented separately; clients recover missed messages through the
cursor-paginated REST history.

## 10. Documents — `documents`

| Method | Endpoint                                                    | Permission           | Purpose                                     |
|:-------|:------------------------------------------------------------|:---------------------|:--------------------------------------------|
| GET    | `/api/v1/projects/{project_id}/documents/`                  | Project member       | List shared documents                       |
| POST   | `/api/v1/projects/{project_id}/documents/`                  | Project member       | Upload document (`multipart/form-data`)     |
| GET    | `/api/v1/documents/{document_id}/`                          | Project member       | Read document metadata and processing state |
| GET    | `/api/v1/documents/{document_id}/download/`                 | Project member       | Download original file                      |
| POST   | `/api/v1/documents/{document_id}/lifecycle-requests/`       | Project member       | Request archive or permanent deletion       |
| POST   | `/api/v1/document-lifecycle-requests/{request_id}/approve/` | Other project member | Approve request                             |
| POST   | `/api/v1/document-lifecycle-requests/{request_id}/reject/`  | Other project member | Reject request                              |
| POST   | `/api/v1/document-lifecycle-requests/{request_id}/cancel/`  | Project member       | Cancel pending deletion request             |
| POST   | `/api/v1/documents/{document_id}/restore/`                  | Project member       | Restore archived document                   |

The document collection supports `page` (default `1`) and `page_size`
(default `20`, maximum `100`). Its default view, equivalent to
`status=active`, contains `active` and `archive_pending` documents.
`status=archived` and `status=deletion_pending` select those respective
states. Archived and deletion-pending documents are absent from the
active view; deleted documents are never returned as content.

Uploads use `multipart/form-data` with a `file` field. The server accepts
only `.pdf`, `.docx`, `.txt`, `.md`, and `.markdown`, validates the
extension against detected content, ignores browser-supplied MIME as
evidence, and rejects files larger than `20 * 1024 * 1024` bytes with
`413`; unsupported or mismatched files return `415`. The response
contains shared metadata and `processing_status=queued`; it omits the
internal storage key and any public file URL.
Zero-byte TXT and Markdown files are valid text uploads and also remain
queued until Stage 09 processing is available.

All documents are shared. There is no private-document API or visibility
flag. Both active participants can upload, list, read metadata, and
download. Every download is authorized on the backend and streamed as an
attachment; file bytes have no public URL. Cross-project or inactive
membership resource IDs return `404`.

Create a lifecycle request with
`{"action":"archive"}` or
`{"action":"permanent_delete"}`. The `201` response contains the
request `id`, `document_id`, `action`, `initiated_by_id`, `status`, both
participants’ recorded approvals, the current viewer’s decision, and
`deletion_after`, `created_at`, and `completed_at` timestamps. The
initiating participant’s approval is recorded with the request. Both
active project roles must exist before a request can be started; a
request requires a `draft` or `active` project. Archive is available
only for an `active` document. It becomes `archive_pending` until the
other active participant decides. Approval moves it to `archived`; a
rejection returns it to `active`.

Permanent deletion is available only for an `archived` document. The
document remains archived while the second approval is pending. The
second approval moves it to `deletion_pending` and sets
`deletion_after` to exactly 30 days after that approval. The deletion
cancellation endpoint accepts either active project member only while
the current time is strictly earlier than `deletion_after`; at the
deadline, cancellation returns `409`. Cancellation marks the request
cancelled and returns the document to `archived`. Restoration is a
separate action: either active project member can restore an archived
document to `active` while the parent project is `draft` or `active`.
If restoration is requested while a permanent-delete request is still
pending after only the initiator's approval, the restore transaction
cancels that request and records both actions. An already approved
deletion must be explicitly cancelled before the document can be
restored.
An archive rejection leaves the file active; a deletion rejection
leaves it archived.

Request creation, approval/rejection, and restoration require an active
member and a mutable parent project (`draft` or `active`). Cancellation
remains available to an active member before the deadline even if the
parent project has since completed or been archived; it withdraws
previous consent. A scheduled deletion that has already reached its
deadline also completes after a parent project is completed or archived.
Cross-project and inactive-member resource IDs return `404`; approving
or rejecting one’s own request returns `403`.

Celery Beat runs an idempotent deletion sweep every five minutes. It
removes the source file and any existing document derivatives, clears
content-bearing metadata, marks the document deleted, and records a
content-free audit event. Cancelled and stale requests are ignored. The
document row and lifecycle consent records remain as a minimal tombstone
and audit trail. Encrypted backups may retain deleted files until their
applicable operational expiry; no fixed backup period or immediate
purge from every backup is promised.

## 11. Project State — `project_state`

| Method | Endpoint                                        | Permission     | Purpose                            |
|:-------|:------------------------------------------------|:---------------|:-----------------------------------|
| GET    | `/api/v1/projects/{project_id}/state/`          | Project member | Get shared Project State aggregate |
| GET    | `/api/v1/projects/{project_id}/evidence-options/` | Executor     | List questionnaire answers that can be cited |
| GET    | `/api/v1/projects/{project_id}/stages/`         | Project member | List stages                        |
| POST   | `/api/v1/projects/{project_id}/stages/`         | Executor       | Create stage                       |
| PATCH  | `/api/v1/stages/{stage_id}/`                    | Executor       | Update stage                       |
| GET    | `/api/v1/projects/{project_id}/requirements/`   | Project member | List requirements                  |
| POST   | `/api/v1/projects/{project_id}/requirements/`   | Executor       | Create requirement                 |
| PATCH  | `/api/v1/requirements/{requirement_id}/`        | Executor       | Update requirement                 |
| GET    | `/api/v1/projects/{project_id}/tasks/`          | Project member | List tasks                         |
| POST   | `/api/v1/projects/{project_id}/tasks/`          | Executor       | Create task                        |
| PATCH  | `/api/v1/tasks/{task_id}/`                      | Executor       | Update task                        |
| GET    | `/api/v1/projects/{project_id}/open-questions/` | Project member | List open questions                |
| POST   | `/api/v1/projects/{project_id}/open-questions/` | Executor       | Create open question               |
| PATCH  | `/api/v1/open-questions/{question_id}/`         | Executor       | Update/resolve question            |
| GET    | `/api/v1/projects/{project_id}/conflicts/`      | Project member | List recorded conflicts            |
| POST   | `/api/v1/projects/{project_id}/conflicts/`      | Executor       | Create conflict with evidence      |
| PATCH  | `/api/v1/conflicts/{conflict_id}/`              | Executor       | Resolve conflict                   |

The aggregate endpoint returns shared Project State counts and links to
the scoped collections; it does not return unbounded entity history. The
collections use page pagination with a default page size of 20 and a
maximum of 100, with stable ordering. AI analyses and pending AI
proposals are excluded. Clients that need the complete collection follow
each response's `next` link until it is `null`.

The customer can read all Project State entities but cannot directly
create or modify them. The customer contributes through chat and
questionnaire responses.

Project State collection reads require active project membership. Writes
require executor membership and project status `draft` or `active`;
completed and archived projects are read-only. Record updates validate
the approved per-entity transition graph in ADR-012. Terminal records
cannot be reopened. For terminal stages, requirements, tasks, and open
questions, an executor may update supported content fields while omitting
`status`; supplying `status` is rejected. A resolved or dismissed
`ProjectConflict` is immutable: every later PATCH is rejected with `409`.
The UI shows terminal statuses without an editable status selector, keeps
content edits available for terminal stages, requirements, tasks, and
questions, and hides edit controls for terminal conflicts. A record ID
outside the project is returned as 404.
Conflict creation accepts at least two distinct evidence references.
Questionnaire answers are resolved through the questionnaire app, and
Message references are resolved through the chat app's read selector;
both sources must belong to the same project. Evidence options remain
executor-only and are sourced through the questionnaire app.
Conflict PATCH is only available while the conflict is `unresolved` and
is used to resolve or dismiss it; resolution records the actor and
timestamp. Resolved and dismissed conflicts cannot be edited again.
Audit metadata contains target identifiers, changed field names, and
status transitions, never user-entered content.

## 12. AI Assistant — `ai_assistant`

| Method | Endpoint                                           | Permission | Purpose                             |
|:-------|:---------------------------------------------------|:-----------|:------------------------------------|
| POST   | `/api/v1/projects/{project_id}/ai/analyses/`       | Executor   | Start manual analysis; asynchronous |
| GET    | `/api/v1/projects/{project_id}/ai/analyses/`       | Executor   | List analysis runs                  |
| GET    | `/api/v1/projects/{project_id}/ai/analyses/{request_id}/` | Executor | Poll a queued analysis request      |
| GET    | `/api/v1/projects/{project_id}/ai/proposals/`      | Executor   | List proposals                      |
| GET    | `/api/v1/ai/proposals/{proposal_id}/`              | Executor   | Read proposal and evidence          |
| POST   | `/api/v1/ai/proposals/{proposal_id}/accept/`       | Executor   | Accept proposal                     |
| POST   | `/api/v1/ai/proposals/{proposal_id}/reject/`       | Executor   | Reject proposal                     |
| POST   | `/api/v1/ai/proposals/{proposal_id}/apply-edited/` | Executor   | Edit and apply proposal             |

AI analysis and proposals are private to the executor. AI model profiles
are configured through restricted backend administration in the MVP;
they are not exposed to customers.

Starting an analysis requires an `Idempotency-Key` UUID header and returns
the durable request UUID and current status with HTTP 202. The same key from
the same executor and project returns the original request. Only manual
executor-triggered analysis is enabled; no chat, questionnaire, document, or
Project State event starts analysis automatically. AI-time evidence excerpts
stay in AI-owned tables until an approved change creates shared Project State.

Applying a proposal must be idempotent and transactional with the
corresponding Project State change.

## 13. Specifications — `specifications`

| Method | Endpoint                                                | Permission     | Purpose                        |
|:-------|:--------------------------------------------------------|:---------------|:-------------------------------|
| GET    | `/api/v1/projects/{project_id}/specification/`          | Project member | Read specification             |
| POST   | `/api/v1/projects/{project_id}/specification/generate/` | Executor       | Queue specification generation |
| PATCH  | `/api/v1/projects/{project_id}/specification/`          | Executor       | Edit specification draft       |

Customer approval, comments, electronic signatures, and formal version
comparison are out of scope.

`PATCH` accepts only `content` (Markdown) and `version`; a stale version
returns `409 Conflict`. Generation requires an
`Idempotency-Key` UUID, returns `202` with its durable request ID and status,
and repeated keys from the same executor and project return the original
request. `GET` includes the latest generation request status for executor
polling; customer responses omit this operation status while retaining the
shared draft content.
Only one generation may be queued or running per project. A generation uses
the source context captured by its enqueue hash; if the approved passport,
shared Project State, or specification version changes before publication,
the request is marked `superseded` and the existing draft is preserved.

## 14. OpenAPI

Use `drf-spectacular` to generate the OpenAPI schema from the
implementation.

Development endpoints:

- `/api/schema/`
- `/api/docs/`

The schema is used to generate frontend TypeScript types. It must
reflect the implemented API, not a separate manually maintained
contract.

## 15. Idempotency and concurrency

- Use `client_message_id` for message submission retries.
- Use `Idempotency-Key` for important create/launch operations where
  duplicate execution would be harmful.
- Use optimistic concurrency (`version`) for passport and specification
  updates.
- Return `409 Conflict` when a client attempts to overwrite a newer
  version.
- Background tasks must be safe to retry.

## 16. Asynchronous operations

Long-running document processing, AI analysis, embedding creation, and
specification generation run through Celery.

The API returns the resource or job identifier and current status.
Clients poll the relevant resource endpoint until it reaches a terminal
state. Do not keep ordinary HTTP requests open while an LLM or document
parser runs.
