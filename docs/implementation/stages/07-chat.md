# Stage 07 — Project Chat

**Goal:** Provide persisted one-to-one project communication with
real-time message delivery.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Chat
- `docs/api/API_CONTRACT.md` — Chat and WebSocket
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/architecture/SYSTEM_ARCHITECTURE.md`

## Dependencies

Stages 02, 03, and 06.

## Scope

### Backend

- Implement Message model and migrations.
- Implement paginated message history.
- Implement message submission with `client_message_id` idempotency.
- Persist messages before publishing real-time events.
- Configure Django Channels routing and authenticated WebSocket
  consumers.
- Verify active project membership on every WebSocket connection.
- Publish `message.created` events to the correct project group only.
- Handle reconnects through REST history retrieval.
- Prevent duplicate message creation on client retries.
- Keep WebSocket delivery separate from persistence.

### Frontend

- Chat panel/page using FSD.
- Load paginated message history.
- Submit text messages.
- Receive new messages over WebSocket.
- Reconnect and recover missed messages through REST.
- Handle duplicate event delivery and optimistic UI state safely.
- Show sending, sent, and failed states.

## Out of scope

- File attachments.
- Message editing/deletion.
- Read receipts.
- Typing indicators.
- Group chat or multiple customers.
- Voice/video calls.

If the product owner later includes any of these, update the scope and
API contract first.

## Deliverables

- Message model and API.
- WebSocket consumer and routing.
- Chat frontend.
- Idempotency and reconnect handling.
- Tests for persistence, delivery, authorization, and duplicate
  requests.

## Acceptance criteria

- [ ] Both project participants can read project message history.
- [ ] Both participants can send text messages.
- [ ] Messages are persisted in PostgreSQL.
- [ ] A new message is delivered to the other participant over
  WebSocket.
- [ ] Reconnecting clients can recover messages missed while
  disconnected.
- [ ] Retrying the same client message ID does not create a duplicate.
- [ ] Non-members cannot connect to or subscribe to a project’s chat.
- [ ] A user cannot receive events from another project.
- [ ] Tests cover unauthenticated connections, non-membership,
  duplicates, and reconnect behavior.

## Stop conditions

If the current product scope includes attachments or message mutation,
do not add them by assumption. Ask for an explicit scope update.

## Codex handoff

Implement Stage 07 only. REST persistence is authoritative; WebSocket is
the real-time delivery mechanism.
