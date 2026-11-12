# Манифест требований

Источник: `2026-11-12-brief.md` и пять названных там брифов этапов 04–08. Строку из этого списка может снять **только пользователь**.

| ID | Из задачи (дословно) | Статус | Основание | Где |
|----|---------------------|--------|-----------|-----|
| R01 | “Only an executor can create or revoke invitations for their project.” | done | - | spec 4.1 and 5; tickets T01; commit f427226 |
| R02 | “An invitation is bound to one normalized email address.” | done | - | spec 4.1 and 5; tickets T01; commit f427226 |
| R03 | “Only the authenticated user with the matching verified email can accept it.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R04 | “Expired and revoked invitations cannot be accepted.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R05 | “Raw invitation tokens are not stored in the database or logs.” | done | ASSUMPTION: raw token is email-only and never in the create response, minimizing token exposure. | spec 4.1 and 5; tickets T01; commit f427226 |
| R06 | “Repeated acceptance does not create duplicate memberships.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R07 | “A project cannot acquire a second active customer.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R08 | “Accepting an invitation for a `draft` project changes its status to `active` in the same transaction as customer membership creation.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R09 | “Accepting an invitation for an `active` project leaves its status `active`; invitations for `completed` or `archived` projects cannot be accepted.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R10 | “Invitations cannot be created or revoked for `completed` or `archived` projects.” | done | - | spec 4.1 and 5; tickets T01; commit f427226 |
| R11 | “Invitation endpoints do not leak project information for invalid tokens.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R12 | “Local invitation delivery is testable through the console email backend.” | done | - | spec 4.1 and 5; tickets T01; commit f427226 |
| R13 | “Tests cover email mismatch, expiry, revocation, replay, and duplicate acceptance.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R14 | “Executor invitation form.” | done | - | spec 4.1 and 5; tickets T01; commit f427226 |
| R15 | “Invitation status/list view.” | done | - | spec 4.1 and 5; tickets T01; commit f427226 |
| R16 | “Invitation landing/preview screen.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R17 | “Login/register path for invited customers.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R18 | “Acceptance confirmation and clear email-mismatch/expired/revoked states.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R19 | “Customer project entry after successful acceptance.” | done | - | spec 4.1 and 5; tickets T02; commit a011ffb |
| R20 | “If invitation expiry duration or email-verification behavior is not configured in the technical documents, select no hidden policy. Propose a default and ask for approval before hard-coding a product-facing duration.” | done | ASSUMPTION: invitation expiry is 7 days; matching verified normalized email follows existing account contract. | spec 4.1 and 5; tickets T01; commit f427226 |
| R21 | “Rate-limit public invitation preview/acceptance endpoints.” | done | ASSUMPTION: preview 30/hour/IP; accept 10/hour/user; create 20/hour/executor. | spec 4.1 and 5; tickets T02; commit a011ffb |
| R22 | “The correct questionnaire schema is selected for each project type.” | done | - | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R23 | “Branching is deterministic and validated by the backend.” | done | - | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R24 | “Prefilled answers are distinguishable from customer-provided answers.” | done | - | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R25 | “Answers are stored separately from passport fields.” | done | - | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R26 | “Submission is atomic and locks the submitted version.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R27 | “Passport changes follow only the approved mapping table.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R28 | “Conflicting values and their sources are preserved.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R29 | “No conflicting value is silently overwritten.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R30 | “Correction/resubmission preserves historical submitted data.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R31 | “AI is not used to generate or branch questionnaire questions.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R32 | “Tests cover every schema branch and conflict behavior.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R33 | “The exact questions and branching rules for all four project types.” | done | ASSUMPTION: four product-authored, immutable version-1 schemas with deterministic type branches. | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R34 | “Required fields and validation rules.” | done | ASSUMPTION: required goal/audience/result/scope; optional deadline, constraints and budget with explicit currency/range checks. | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R35 | “Versioning and compatibility rules for questionnaire schemas.” | done | ASSUMPTION: immutable numbered schema versions; correction retains the original version. | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R36 | “Exact answer-to-passport mapping rules.” | done | ASSUMPTION: explicit mapping is documented in spec section 3; no label-based inference. | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R37 | “Whether correction requests reopen a submission or create a new superseding submission.” | done | ASSUMPTION: correction creates a superseding draft; submitted history is preserved. | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R38 | “Where deterministic questionnaire/passport conflicts are shown and how the executor resolves them.” | done | ASSUMPTION: executor-only conflict queue; keep current passport or apply answer via versioned project service. | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R39 | “Store questionnaire definitions as versioned JSON files in the backend repository.” | done | - | spec 3, 4.2 and 5; tickets T03; commit ea20ae1 |
| R40 | “Executor view of submission status and unresolved conflicts.” | done | - | spec 3, 4.2 and 5; tickets T04; commit e50dcb2 |
| R41 | “Both participants can read every shared Project State entity in their project.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R42 | “Only the executor can create or modify structured Project State entities.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R43 | “A customer cannot modify state by calling the API directly.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R44 | “Cross-project IDs cannot be used to read or mutate another project’s records.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R45 | “Conflict records retain source references and resolution history.” | done | ASSUMPTION: T06 provides questionnaire-answer sources; T07 adds same-project message sources; snapshots are immutable. | spec 3, 4.3 and 5; tickets T06, T07 |
| R46 | “AI-only analyses and proposals are excluded from customer responses.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R47 | “No completion percentage is stored or displayed.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R48 | “All implemented status transitions match the approved state machine.” | done | - | spec 3, 4.3 and 5; tickets T05; commit 0009b3f |
| R49 | “Tests cover role boundaries, invalid transitions, and project isolation.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R50 | “Implement ProjectStage, Requirement, Task, OpenQuestion, ProjectConflict, and Evidence models.” | done | - | spec 3, 4.3 and 5; tickets T05; commit 0009b3f |
| R51 | “Implement the Project State aggregate read endpoint.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R52 | “Implement CRUD/action endpoints listed in the API contract.” | done | - | spec 3, 4.3 and 5; tickets T05; commit 0009b3f |
| R53 | “Shared Project State view for both roles.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R54 | “Executor controls for creating and editing stages, requirements, tasks, questions, and conflict resolutions.” | done | - | spec 3, 4.3 and 5; tickets T05; commit 0009b3f |
| R55 | “Customer read-only view.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R56 | “Clear status and due-date presentation.” | done | - | spec 3, 4.3 and 5; tickets T06; commit ce6c3b5 |
| R57 | “Finalize status choices and allowed transitions for stages, requirements, tasks, open questions, and conflicts.” | done | ASSUMPTION: state enums and transitions are fixed in spec section 3. | spec 3, 4.3 and 5; tickets T05; commit 0009b3f |
| R58 | “Confirm the statuses and allowed state transitions for stages, requirements, tasks, open questions, and conflicts before implementing state-transition logic.” | done | ASSUMPTION: listed terminal states cannot be reopened. | spec 3, 4.3 and 5; tickets T05; commit 0009b3f |
| R59 | “Both project participants can read project message history.” | done | - | spec 3, 4.4 and 5; tickets T07 |
| R60 | “Both participants can send text messages.” | done | - | spec 3, 4.4 and 5; tickets T07 |
| R61 | “Messages are persisted in PostgreSQL.” | done | - | spec 3, 4.4 and 5; tickets T07 |
| R62 | “A new message is delivered to the other participant over WebSocket.” | done | - | spec 3, 4.4 and 5; tickets T08; commit a2a6880 |
| R63 | “Reconnecting clients can recover messages missed while disconnected.” | done | - | spec 3, 4.4 and 5; tickets T08; commit a2a6880 |
| R64 | “Retrying the same client message ID does not create a duplicate.” | done | - | spec 3, 4.4 and 5; tickets T07 |
| R65 | “Non-members cannot connect to or subscribe to a project’s chat.” | done | - | spec 3, 4.4 and 5; tickets T08; commit a2a6880 |
| R66 | “A user cannot receive events from another project.” | done | - | spec 3, 4.4 and 5; tickets T08; commit a2a6880 |
| R67 | “Tests cover unauthenticated connections, non-membership, duplicates, and reconnect behavior.” | done | - | spec 3, 4.4 and 5; tickets T08; commit a2a6880 |
| R68 | “Implement paginated message history.” | done | ASSUMPTION: chat history page size 50, maximum 100, stable cursor order. | spec 3, 4.4 and 5; tickets T07 |
| R69 | “Show sending, sent, and failed states.” | done | ASSUMPTION: message limit 10,000 chars; sending only while active; new submissions are limited to 60/user/fixed UTC minute via REST; WebSocket is event delivery only. | spec 3, 4.4 and 5; tickets T07 |
| R70 | “File attachments.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 |
| R71 | “Message editing/deletion.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 |
| R72 | “Read receipts.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 |
| R73 | “Typing indicators.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 |
| R74 | “Group chat or multiple customers.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 |
| R75 | “Voice/video calls.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 |
| R76 | “Both participants can list, upload, and download all project documents.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R77 | “No private-document visibility concept exists.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R78 | “Files larger than 20 MB are rejected server-side.” | done | ASSUMPTION: maximum file size is exactly 20*1024*1024 bytes. | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R79 | “Unsupported formats are rejected server-side.” | done | ASSUMPTION: accept listed extensions only when detected content agrees. | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R80 | “Original filenames cannot cause path traversal or overwrite another file.” | done | ASSUMPTION: generated UUID storage key is independent of display filename. | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R81 | “Downloads require active project membership.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R82 | “Archive requires approval from both participants.” | done | ASSUMPTION: archive stays pending until both participants approve; rejection leaves it active. | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R83 | “An archived document is absent from the active list and can be restored.” | done | ASSUMPTION: archived files leave the active list and remain restorable. | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R84 | “Permanent deletion requires both participants’ explicit consent.” | done | ASSUMPTION: permanent deletion needs both explicit approvals. | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R85 | “Permanent deletion follows the approved archive-first sequence.” | done | ASSUMPTION: archive-first is enforced; deletion request only starts from archived. | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R86 | “Lifecycle actions are audited.” | done | - | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R87 | “Tests cover upload limits, invalid MIME types, unauthorized downloads, consent, rejection, restoration, and deletion eligibility.” | done | - | spec 3, 4.5, 5 and 7; ticket T10 (including T09 upload/download tests) |
| R88 | “Implement Document, DocumentLifecycleRequest, and DocumentLifecycleApproval.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R89 | “Store bytes outside PostgreSQL using a storage abstraction and persistent local volume.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R90 | “Validate file extension and detected MIME type.” | done | ASSUMPTION: validate MIME by file signature/structure or safe text decoding, not browser Content-Type. | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R91 | “Generate internal storage keys; never use original filenames as filesystem paths.” | done | ASSUMPTION: generated server-side storage key never derives from original filename. | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R92 | “Exclude archived and deletion-pending documents from active lists and future retrieval.” | done | - | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R93 | “Shared project document list.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R94 | “Upload control with size/type validation feedback.” | done | - | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R95 | “Document details and processing/lifecycle status.” | done | ASSUMPTION: valid files remain queued until Stage 09 processing exists; Stage 08 does not claim extraction. | spec 3, 4.5, 5 and 7; ticket T09; commit 9f45b90 |
| R96 | “Archive request, approval/rejection, restore, and deletion request UI.” | done | - | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R97 | “Also confirm whether the documented 30-day cancellation window is approved. Do not hard-code an unconfirmed grace period.” | done | ASSUMPTION: cancellation window is 30 days from second approval. | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R98 | “The current lifecycle/API documents do not clearly enforce that archive-first sequence. Resolve and update the state machine, database model, and API contract before implementation.” | done | ASSUMPTION: cancelled deletion returns document to archived; restore remains separate. | spec 3, 4.5, 5 and 7; tickets T10; commit ab19730 |
| R99 | “Full-text extraction and embeddings; those are Stage 09.” | deferred | Deferred: explicitly outside the current stages or assigned to Stage 09. | spec 8 and 9 |
| R100i | *(подразумевается)* Users must be able to complete each stage’s workflow through the application UI and authenticated API, with backend-enforced permissions. | done | ASSUMPTION: reuse current protected routes and backend role checks for each workflow. | spec 2, 5, 6 and 7; tickets T01, T02, T03, T04, T05, T06, T07, T08, T09, T10 |
| R101i | *(подразумевается)* Invalid, expired, unavailable, and in-progress states must give users a recoverable outcome rather than a blank or broken screen. | done | ASSUMPTION: loading/empty/error/validation/retry states remain recoverable. | spec 2, 5, 6 and 7; tickets T01, T02, T03, T04, T05, T06, T07, T08, T09, T10 |
| R102i | *(подразумевается)* REST/OpenAPI remains authoritative for resource operations; WebSocket is only the chat delivery channel. | done | ASSUMPTION: REST is source of truth; WebSocket only delivers chat events. | spec 2, 5, 6 and 7; tickets T01, T02, T03, T04, T05, T06, T07, T08, T09, T10 |

## Discovery during implementation

| ID | Discovery | Status | Basis | Effect |
|----|-----------|--------|-------|--------|
| D01 | Chat message submission is REST-only; WebSocket only delivers committed events and has no client send protocol or separate WS send-rate close flow. | discovered | The Stage 07 brief, accepted ADR-005, and R102i establish REST submission and delivery-only WebSocket. T07 implemented the only submission endpoint; T08 exposed the spec's contradictory `4408` clause. No user requirement is removed; the per-user limit applies to REST submissions. | Spec §4.4 and T08 acceptance now describe REST rate limiting and event-only WebSocket. |
| D02 | T09 must mount project-scoped and global document routes in the existing project and root routers, but the integration files were missing from the ticket zone. | discovered | The required list/upload routes are project-scoped and belong in `backend/apps/projects/api/urls.py`; metadata/download routes use global document IDs and belong in `backend/config/urls.py`. | T09 zone expanded to include both router integration points; endpoint paths and authorization scope are unchanged. |
| D03 | Zero-byte TXT/Markdown files are accepted because the Stage 08 contract sets a maximum size but no minimum. | discovered | Empty bytes are valid empty text; adding a positive-size database constraint would invent an unapproved minimum. | Spec §4.5 clarifies zero-byte text files are accepted and remain queued for Stage 09 processing. |
| D04 | T10's lifecycle workflow needs frontend entity API/types, generated OpenAPI types, runtime schedule and product documentation files omitted from the original ticket zone. | discovered | The documented workflow adds REST operations and a Celery Beat sweep, so the API entity/types, Django runtime configuration, deployment schedule, lifecycle docs, and ADR must be updated at their owning boundaries. | T10 zone expanded to include those spec-required integration files; product behavior and endpoint contract are unchanged. |
| D05 | A due deletion already approved by both participants must run even if the parent project later closes; cancellation remains available until the deadline. | discovered | Consent has been collected and the 30-day withdrawal window has elapsed; gating the system sweep on later project status would strand a valid request, while blocking cancellation would prevent either participant from withdrawing consent. | Spec §4.5 clarifies user action gates versus the idempotent system sweep; no user requirement is removed. |
| D06 | Restoring an archived document with a still-pending permanent-delete request cancels that one-party request in the same transaction; an already approved deletion still requires explicit cancellation before restore. | discovered | A pending request records only one participant's consent. Leaving it pending after restoration makes it unapprovable and prevents a new request, while silently retaining that consent after restore contradicts the restored active state. | Spec §4.5, ADR-013, and document lifecycle/API/data-model contracts now define restoration as withdrawal of a pending request; the cancellation and restore are both audited. |
| D07 | Session-authenticated project chat WebSockets must validate the request Origin against configured frontend origins. | discovered | Without this check, a foreign site could attempt to use a participant's browser session to subscribe to project events. The existing `FRONTEND_BASE_URL` and `CSRF_TRUSTED_ORIGINS` provide the allowlist; the originless health probe remains outside the chat authentication stack. | T11 wraps only the project chat route in `OriginValidator`; foreign and missing chat Origin values are rejected, while `/ws/v1/health/` remains available without Origin. ADR-005/security docs record the boundary. |

Начальный статус всех требований — `open`; Phase 2 закроет решения, а Phase 3 сопоставит каждую строку со спецификацией или обоснованным исключением.

## Phase 2 — self-briefing (full mode)

Пользовательские факты, учётные данные, дизайн-эталон, SMTP-провайдер и данные для импорта не указаны. Ничего из этого не выдумываю: использую существующую локальную сессию, консольную почту, Compose-инфраструктуру и текущий UI. Глубина normal, поэтому adversarial pass не запускается.

### ASSUMPTIONS — принято за пользователя

- **R20 - ASSUMPTION:** срок приглашения — 7 суток после создания. Принятый в аккаунтах контракт подтверждения email сохраняется: принять приглашение может только вошедший пользователь с совпадающим подтверждённым нормализованным email.
- **R21 - ASSUMPTION:** preview — до 30 запросов в час на IP; accept — до 10 запросов в час на аккаунт; создавать приглашения — до 20 в час на исполнителя. Счётчики используют общий Redis cache.
- **ASSUMPTION 03 (R33–R34):** четыре неизменяемые схемы версии 1 (`website`, `telegram_bot`, `automation`, `other`). В каждой обязательны цель, аудитория, ожидаемый результат и функциональный охват; integration toggle управляет условным списком интеграций. Ограничения, срок и бюджет необязательны; валюта обязательна при заполнении любого бюджета, минимум не выше максимума. Для `website` — условный URL существующего сайта; для `telegram_bot` — условная ссылка на существующего бота; для `automation` — тип триггера и условные детали для расписания/события; для `other` — уточнение области проекта при выборе «другое».
- **R35 - ASSUMPTION:** schema JSON неизменяемы после выпуска; новые анкеты получают последнюю версию типа проекта, чтение всегда использует версию отправления, correction создаёт новую отправку на версии исходной анкеты.
- **R36 - ASSUMPTION:** явная таблица сопоставления в спецификации: общие ответы → одноимённые поля паспорта; scope и контекст типа проекта → ключ типа в `functional_scope` и версионированный блок `additional_data`; интеграции и ограничения → документированные JSON-формы; срок и бюджеты → одноимённые поля. Пустые необязательные ответы не очищают паспорт.
- **R37 - ASSUMPTION:** запрос коррекции создаёт новую черновую отправку с `supersedes_id`; исходная отправка и ответы остаются неизменными. Исполнитель видит статус и может запросить коррекцию; клиент редактирует только новый черновик.
- **R38 - ASSUMPTION:** конфликт анкеты с непустым полем паспорта сохраняется в очереди проверки, доступной исполнителю. До решения паспорт не меняется. Исполнитель может оставить значение паспорта или применить ответ анкеты; второе действие проходит через сервис паспорта с проверкой версии. Конфликт не становится общим Project State автоматически.
- **ASSUMPTION 08 (R57–R58):** конечные состояния статусов терминальны; ниже указанные переходы исчерпывающие. Stage: `planned → active|cancelled`, `active → blocked|completed|cancelled`, `blocked → active|cancelled`. Requirement: `draft → confirmed|rejected`, `confirmed → in_progress|rejected`, `in_progress → blocked|completed|rejected`, `blocked → in_progress|rejected`. Task: `todo → in_progress|cancelled`, `in_progress → blocked|done|cancelled`, `blocked → in_progress|cancelled`. OpenQuestion: `open → resolved|dismissed`. ProjectConflict: `unresolved → resolved|dismissed`.
- **ASSUMPTION 09 (R45):** Evidence создаёт исполнитель; допустимые источники в этом этапе — сообщение или ответ анкеты того же проекта. Ссылки и снимок цитаты сохраняются неизменяемо; разрешение конфликта хранит актёра, время, итог и запись аудита. Элементы очереди конфликта анкеты остаются приватными для исполнителя.
- **ASSUMPTION 10 (R68–R69):** сообщения имеют лимит 10 000 символов; история выдаётся курсором по 50 записей (максимум 100) в стабильном порядке. Отправка доступна участникам только в `active`; историю можно читать во всех статусах. Лимит отправки — 60 сообщений в минуту на пользователя для REST и WebSocket.
- **ASSUMPTION 11 (R76–R98):** лимит файла — ровно `20 × 1024 × 1024` байт; принимать только PDF/DOCX/TXT/Markdown при совпадении расширения и сигнатуры/текстового содержимого. Списки приглашений, Project State и документов используют стабильную page pagination, default 20, cap 100. Режим документа: `active → archive_pending → archived → deletion_pending → deleted`; permanent-delete запрашивается только для уже архивированного документа. Окно отмены — существующие в двух технических документах 30 суток от второго одобрения; отмена возвращает состояние `archived`, после чего участник может отдельно восстановить документ. На backup сроки не распространяются и обещаний об их очистке нет.
- **R99 (Deferred):** OCR, извлечение текста, чанки и embeddings остаются этапом 09. Scanned-PDF UX для того будущего процессора помечен как отложенное решение. Сканер вредоносных файлов не добавляется; отсутствие сканирования — production gate.
- **ASSUMPTION 13 (R100i–R102i):** workflows встроены в текущие защищённые маршруты приложения и существующий API-клиент; сервер повторно проверяет роль и проект; REST — источник истины, WebSocket — доставка чата. Для loading/empty/error/validation/retry используются существующие UI-конвенции и никакие права не определяются только frontend.
- **ASSUMPTION 14 (R05):** The raw invitation token appears only in the emailed link; the create API response never returns it, minimizing token exposure.

G1 закрывается перед спецификацией: все требования имеют статус; нерешённых продуктовых строк `open` нет. Отложены только функции, прямо исключённые из этих этапов или принадлежащие Stage 09.
