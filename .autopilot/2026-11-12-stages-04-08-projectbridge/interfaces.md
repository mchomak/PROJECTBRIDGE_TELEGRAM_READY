# Implementation interfaces and project rules

## Frozen seams from the spec

## 6. Границы и швы

| Модуль | Владеет | Выставляет | Прячет |
|---|---|---|---|
| `accounts` (существующий) | User, normalization, verified-email contract | existing normalized User/email verification | auth hashes and verification token storage |
| `projects` (существующий) | Project, ProjectMember, ProjectPassport and project lifecycle | `add_customer_member_from_invitation(*, project_id, user) -> ProjectMember`; `apply_questionnaire_mapping(*, project_id, actor, expected_version, mapped_changes) -> ProjectPassport`; `update_passport(*, project_id, actor, expected_version, changes) -> ProjectPassport` | row locks, constraints, lifecycle audit and optimistic version comparison |
| `invitations` | ProjectInvitation and email-bound token flow | `create_invitation(*, project_id, actor, invited_email)`, `preview_invitation(raw_token)`, `accept_invitation(*, actor, raw_token)`, `revoke_invitation(...)` | token generation/hash, expiration, throttle keys, email construction and safe error mapping |
| `questionnaire` | immutable JSON schemas, submissions, answers, mapping conflicts | `get_questionnaire(project_id, actor)`, `save_answers(submission_id, actor, answers)`, `submit_submission(submission_id, actor)`, `request_correction(submission_id, actor)`, `resolve_conflict(conflict_id, actor, decision, expected_passport_version)` | branch evaluation, schema compatibility, mapping, conflict snapshots and transaction orchestration |
| `project_state` | shared State entities, status machines and Evidence links | project-scoped selectors; services to create/update/resolve each entity; `get_project_state(project_id, actor)` | valid transition graph, evidence source validation, resolution audit, customer-safe serialization |
| `chat` | Message, idempotency and WebSocket group delivery | `list_messages(project_id, actor, cursor, limit)`, `send_message(project_id, actor, client_message_id, content)` | cursor encoding, dedupe, Redis rate keys, channel group/publish timing |
| `documents` | Document metadata/storage/lifecycle request, approvals and deletion scheduler | `list_documents(project_id, actor, status, page)`, `upload_document(project_id, actor, file)`, `request_lifecycle_action(document_id, actor, action)`, `decide_lifecycle_request(request_id, actor, decision)`, `restore_document(document_id, actor)`, `process_expired_deletions()` | signature validation, generated paths, physical deletion, state transitions, backup caveats |
| `common` (существующий) | safe ProjectAuditLog operations | `record_project_action(...)` | metadata allowlist; no project-domain rules |
| Frontend `entities`/`features`/`pages` | API models/queries, user actions, route composition | typed API functions and mutation hooks | session/CSRF stays in shared API client; no business authorization in UI |
| Runtime config | Channels + Redis; Celery worker + Beat; persistent media | ASGI chat routing; five-minute deletion sweep | deployment credentials and provider credentials remain backend-only |

**Test seams:** project public services/selectors; each app service and DRF endpoint; WebSocket communicator through ASGI; Django default storage; Celery task invoked directly and through scheduled config; frontend pages/hooks with mocked typed API. Database constraints, service validation, and endpoint permissions are verified at their owning boundary. Cross-module writes use the owner services; no app directly mutates another app’s models.

## Project rules the ticket context may not infer

- Stack pins: Python 3.13.18, Django 5.2.19, DRF, PostgreSQL 17 with pgvector 0.8.7, Redis 7.4.12, Celery 5.7.0, Channels 4.3.2; Node 24.22.2, React 19.3.1, Vite 8.3.7, React Router 7, TypeScript.
- Django is a modular monolith. Each app owns its models and writes. Put state changes in its services and reads in its selectors. Views stay thin; serializers validate shapes but do not own domain rules. Never directly mutate another app's models.
- Frontend dependency direction is app -> pages -> widgets -> features -> entities -> shared. API types come from drf-spectacular and the generated schema. Never edit generated types manually.
- REST is the resource/source-of-truth API. WebSocket only delivers chat events. Browser auth uses same-origin session cookies and CSRF; never store credentials in browser storage.
- PostgreSQL is authoritative. Celery jobs must be retry-safe and enqueued after commit. Audit metadata must not contain tokens, passwords, message/file content, or provider secrets.
- Keep additive migrations; do not edit Stage 01-03 migrations or delete/replace local volumes. Do not run `docker compose down -v`. `.env` values are secret: do not read them into output or commit them.
- Work only in the ticket's named zones and required documentation. Do not revert another contributor's changes. If a dependency is missing, return `BLOCKED`; do not install packages or change runtime pins.
- Run the acceptance checks named in the ticket and relevant project checks. Backend source is baked into Compose images; rebuild backend after backend edits. Frontend source is baked into its image; rebuild/recreate frontend after frontend edits.
- At each stage boundary, commit the reviewed stage work to local `main`, then attempt push to the already configured upstream. The checkout currently has no remote; never invent one and record the failed push.

## Existing verification commands

Backend, from the repo root with existing Compose images:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend python manage.py makemigrations --check --dry-run
docker compose run --rm --no-deps backend python manage.py spectacular --validate --file /tmp/openapi.yml
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
```

Frontend:

```sh
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose run --build --rm --no-deps frontend npm test
docker compose exec frontend npm run build
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
docker compose cp frontend:/app/src/shared/api/generated/schema.d.ts frontend/src/shared/api/generated/schema.d.ts
```

## From ticket T01 - invitation management

- `create_invitation(*, project_id, actor, invited_email) -> ProjectInvitation`
- `get_project_invitations(*, project_id, actor)` returns paginated `InvitationListResponse` with `count`, `next`, `previous`, and `results`.
- `revoke_invitation(*, project_id, actor, invitation_id) -> ProjectInvitation`
- Project API: `GET/POST /api/v1/projects/{project_id}/invitations/`; `POST /api/v1/projects/{project_id}/invitations/{invitation_id}/revoke/`.
- Status values: `pending|accepted|revoked|expired`.
- The raw token appears only in the outbound email link (`/invite/#token=<token>`); create responses omit token/link. Storage keeps only the hash.
- Expiry: seven days. Creation throttle: 20 per executor per UTC hour. Public preview and acceptance are owned by T02.

## From ticket T02 - invitation preview and acceptance

- `POST /api/v1/invitations/preview/` accepts `{token}` and returns `{project_name,email_hint,expires_at,status}`. Unknown token: 404; expired/revoked: 410; completed/archived project: 409; rate limit: 429.
- `POST /api/v1/invitations/accept/` accepts `{token}` and returns `{invitation_id,project_id,status}`. Matching verified normalized email is required; mismatch/unverified: 403; same-user replay is idempotent; status conflict: 409; expired/revoked: 410; rate limit: 429.
- Project owner service: `projects.services.add_customer_member_from_invitation(*, project_id, user) -> ProjectMember`; membership and draft-to-active transition are atomic.
- Preview throttle: 30/hour/IP. Acceptance throttle: 10/hour/user.
- Public route: `/invite/`; it reads the token from URL fragment, keeps it out of URLs sent to the server, and sends it only in preview/accept POST bodies.

## From ticket T07 - persisted chat and REST history

- `chat.Message` owns project-scoped message persistence. `send_message(*, project_id, actor, client_message_id, content) -> SendMessageResult(message, created)` verifies active membership, normalizes and bounds content, returns an identical idempotent replay before the active-project check, and only allows new writes while the project is active. Conflicting content returns 409; inactive members cannot replay.
- `list_messages(*, project_id, actor, cursor=None, limit=50) -> MessagePage(results, next_cursor, previous_cursor)` uses signed `(created_at, id)` keyset cursors. History is newest-first; UI renders chronologically. `enforce_chat_send_rate_limit(*, actor_id, now=None)` is the shared 60/user/fixed-UTC-minute Redis limiter used by REST message submissions. T08 remains event-only and does not add a WebSocket send protocol.
- REST routes: `GET, POST /api/v1/projects/{project_id}/messages/`. Persisted message sends are the source of truth; the `send_message` service is the seam T08 extends to publish `message.created` only after commit, and idempotent replays must not publish duplicates.
- `apps.chat.selectors.get_message_for_evidence(project_id, message_id)` is the source resolver used by Project State. Keep message reads in `chat`; do not mutate chat records from `project_state`.
- Frontend chat API/query and mutation exports live in `frontend/src/entities/chat/` and `frontend/src/features/chat/`. `ChatPage` loads the REST history, preserves failed content and `client_message_id` for retry, and must recover missed events from REST after WebSocket reconnect.

## From ticket T08 - authenticated WebSocket delivery

- `backend/apps/chat/routing.py` routes `/ws/v1/projects/{project_id}/chat/` to the chat consumer through the ASGI `AuthMiddlewareStack`. The consumer accepts only authenticated active project members and joins a group scoped to that project. It is event-delivery-only; do not add a client message submission protocol.
- `send_message` publishes `message.created` through `transaction.on_commit` only for a newly-created message. Idempotent replay returns the existing REST response without publishing another event. REST `POST` remains the message submission and rate-limit boundary.
- The frontend ChatPage receives events, merges by `message.id`, and reloads paginated REST history on connection/reconnection. Failed REST submissions (including 429) retain content and the original `client_message_id` for retry.

## From ticket T09 - shared document storage and access

- `documents` owns `Document`, `DocumentLifecycleRequest`, `DocumentLifecycleApproval`, storage, and document selectors/services. T09 exposes project collection `GET, POST /api/v1/projects/{project_id}/documents/` and global metadata/download `GET /api/v1/documents/{document_id}/` and `/download/`; project collection mounts through `projects/api/urls.py`, global document IDs through `config/urls.py`.
- Both active project roles can list, upload, and download shared documents; every metadata/download lookup is membership-scoped. No public file URL or private-document field exists. Upload is allowed only in `draft|active` projects.
- Files are written using Django default storage on the existing persistent media volume. Storage keys are generated UUID names independent of display names; server computes SHA-256. Server validation checks extension/content for PDF, DOCX, TXT, MD/Markdown, enforces 20 MiB max, and rejects unsafe/binary text. Empty TXT/Markdown is accepted and stays `queued` until Stage 09. Failed metadata creation compensates by deleting stored bytes.
- T09 provides shared list/upload/details/queued status/download UI. The rows/models also establish the schema for T10 lifecycle actions; archive/approval/deletion state transitions are not yet implemented.

## From ticket T10 - mutual-consent document lifecycle

- Lifecycle services remain owned by `documents`: `request_lifecycle_action(document_id, actor, action)`, `decide_lifecycle_request(request_id, actor, decision)`, `restore_document(document_id, actor)`, and `process_expired_deletions()`. The request creator's approval is recorded atomically; the other active project member supplies the second decision.
- Routes: `POST /api/v1/documents/{document_id}/lifecycle-requests/`; `POST /api/v1/document-lifecycle-requests/{request_id}/{approve|reject|cancel}/`; `POST /api/v1/documents/{document_id}/restore/`. The collection adds status views for active, archived, and deletion-pending documents.
- Archive transitions `active → archive_pending → archived`; rejection returns to active. Permanent deletion can start only from archived and becomes `deletion_pending` after second approval, setting the 30-day deadline at that time. Restore is separate and status-gated. An active member may cancel before deadline even after project closure; the five-minute sweep completes due approved deletions regardless of later project status (D05).
- `process_expired_deletions` is retry-safe and scheduled through Celery Beat every 300 seconds. It ignores cancelled/stale requests, scrubs content-bearing metadata, removes file bytes, and leaves only minimal audit metadata. Existing encrypted backups follow the previously documented caveat; no immediate or fixed backup-purge promise is made.
- Frontend lifecycle actions live in the Documents entity/features/panel. UI displays mutual consent, pending decision, deadline countdown, cancellation and restore actions; actual role/state authorization remains server-side.
