# ProjectBridge API Contract

**Status:** Endpoint baseline; Stage 02 authentication schemas finalized;
other request/response schemas remain to be finalized  
**API version:** v1  
**Last updated:** 2026-11-11

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

## 8. Questionnaire — `questionnaire`

| Method | Endpoint                                                                | Permission                    | Purpose                                      |
|:-------|:------------------------------------------------------------------------|:------------------------------|:---------------------------------------------|
| GET    | `/api/v1/projects/{project_id}/questionnaire/`                          | Project member                | Get applicable schema and current submission |
| POST   | `/api/v1/projects/{project_id}/questionnaire/submissions/`              | Customer                      | Start a submission                           |
| PATCH  | `/api/v1/questionnaire/submissions/{submission_id}/answers/`            | Customer, editable state only | Save answers                                 |
| POST   | `/api/v1/questionnaire/submissions/{submission_id}/submit/`             | Customer                      | Validate and submit                          |
| POST   | `/api/v1/questionnaire/submissions/{submission_id}/request-correction/` | Executor                      | Request customer correction                  |

Questionnaire definitions are versioned JSON files in the backend
repository. Backend validation is authoritative for required fields and
branching rules.

A submitted questionnaire is locked. The correction/revision mechanism
must preserve prior submitted data; whether corrections reopen the same
submission or create a superseding submission is still to be finalized.

On submission, the backend applies deterministic passport mappings.
Non-conflicting values may update the passport. Conflicting values are
preserved and recorded for executor review; no silent overwrite is
allowed.

## 9. Chat — `chat`

| Method | Endpoint                                  | Permission     | Purpose                        |
|:-------|:------------------------------------------|:---------------|:-------------------------------|
| GET    | `/api/v1/projects/{project_id}/messages/` | Project member | Read paginated message history |
| POST   | `/api/v1/projects/{project_id}/messages/` | Project member | Submit a message               |

WebSocket:

`/ws/v1/projects/{project_id}/chat/`

The WebSocket connection uses the authenticated session and must verify
active project membership. REST is used for persistence and message
submission; WebSocket delivers events such as `message.created`. After
reconnecting, clients retrieve missed messages through REST.

Use a client-generated message identifier to make retries idempotent.

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

All documents are shared. There is no private-document API or visibility
flag. Both participants can upload.

Archive and permanent deletion require consent from both participants.
The initiating participant’s request records their approval; the other
participant must approve. Permanent deletion has a 30-day cancellation
window after both approvals.

## 11. Project State — `project_state`

| Method | Endpoint                                        | Permission     | Purpose                            |
|:-------|:------------------------------------------------|:---------------|:-----------------------------------|
| GET    | `/api/v1/projects/{project_id}/state/`          | Project member | Get shared Project State aggregate |
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
| PATCH  | `/api/v1/conflicts/{conflict_id}/`              | Executor       | Resolve conflict                   |

The aggregate endpoint returns only shared Project State data. AI
analyses and pending AI proposals are excluded.

The customer can read all Project State entities but cannot directly
create or modify them. The customer contributes through chat and
questionnaire responses.

## 12. AI Assistant — `ai_assistant`

| Method | Endpoint                                           | Permission | Purpose                             |
|:-------|:---------------------------------------------------|:-----------|:------------------------------------|
| POST   | `/api/v1/projects/{project_id}/ai/analyses/`       | Executor   | Start manual analysis; asynchronous |
| GET    | `/api/v1/projects/{project_id}/ai/analyses/`       | Executor   | List analysis runs                  |
| GET    | `/api/v1/projects/{project_id}/ai/proposals/`      | Executor   | List proposals                      |
| GET    | `/api/v1/ai/proposals/{proposal_id}/`              | Executor   | Read proposal and evidence          |
| POST   | `/api/v1/ai/proposals/{proposal_id}/accept/`       | Executor   | Accept proposal                     |
| POST   | `/api/v1/ai/proposals/{proposal_id}/reject/`       | Executor   | Reject proposal                     |
| POST   | `/api/v1/ai/proposals/{proposal_id}/apply-edited/` | Executor   | Edit and apply proposal             |

AI analysis and proposals are private to the executor. AI model profiles
are configured through restricted backend administration in the MVP;
they are not exposed to customers.

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
