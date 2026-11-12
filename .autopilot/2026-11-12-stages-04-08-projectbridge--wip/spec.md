# Спецификация: ProjectBridge, этапы 04–08

## 1. Задача

После создания проекта исполнителю нужно безопасно подключить заказчика, собрать от него подтверждённые требования, вести общий план работ, общаться с заказчиком и совместно управлять документами. Сейчас в приложении есть только аккаунты, проекты и паспорт; этапы 04–08 добавляют оставшийся рабочий путь двух участников.

## 2. Решение и пользовательские истории

| Метка | История | Приёмка |
|---|---|---|
| R01–R21 | Как исполнитель, я приглашаю заказчика по нормализованному email и вижу состояние приглашения, чтобы заказчик мог присоединиться к нужному проекту. | Ссылка безопасна, ограничена по сроку, повторное принятие идемпотентно; совпадающий подтверждённый аккаунт становится единственным заказчиком; `draft` атомарно становится `active`. |
| R22–R40 | Как заказчик, я заполняю детерминированную анкету своего типа проекта, а исполнитель может запросить исправление и разрешить расхождения, чтобы паспорт обновлялся только по явным правилам. | Черновик можно продолжить; отправленная версия блокируется; исправление создаёт новую версию; каждое поле сопоставлено явно; конфликтующие источники сохраняются до решения исполнителя. |
| R41–R58 | Как участник проекта, я вижу общий структурированный план; как исполнитель, я могу его вести, чтобы состояние было прозрачным без неподтверждённого процента готовности. | Заказчик читает, но backend блокирует его записи; переходы валидируются; все записи изолированы по проекту; конфликты сохраняют источники и решение. |
| R59–R69 | Как участник проекта, я читаю историю и отправляю текстовые сообщения, чтобы обмениваться ими в реальном времени и не терять их при переподключении. | PostgreSQL сохраняет сообщение до события; повтор того же `client_message_id` не создаёт дубликат; REST восстанавливает пропуски. |
| R76–R98 | Как участник проекта, я загружаю и скачиваю общий файл; мы оба можем архивировать, восстанавливать и согласованно удалять его, чтобы документ не исчезал из-за решения одного человека. | Сервер валидирует размер, расширение, содержимое и членство; архивируемый файл скрывается из активного списка, но остаётся восстанавливаемым; удаление возможно лишь после архивации, двух согласий и окна отмены. |

Экранные подписи и сообщения остаются на английском, как в существующих auth/project-экранах. Новых учётных записей, платных сервисов и внешней отправки данных не требуется. Почта использует настроенный Django backend; локально это console backend.

## 3. Решения, ограничения и продуктовые допущения

- Security decision recorded during T01: only the invitation email contains the raw token; the API response does not expose it.
В полном режиме эти решения приняты за пользователя, чтобы не блокировать пять этапов. Это выбранные продуктовые значения, а не уже существовавшие факты.

1. **Приглашения.** Срок действия — 7 суток. Preview ограничен 30 запросами/час/IP, принятие — 10/час/пользователь, создание — 20/час/исполнитель. Счётчики идут через общий Redis cache. Email-верификация не меняется: принимать приглашение может только вошедший пользователь с совпадающим подтверждённым нормализованным email.
2. **Анкеты.** Четыре product-authored JSON-схемы версии 1 для `website`, `telegram_bot`, `automation`, `other`. Выпущенная версия неизменяема; новые отправления используют последнюю версию своего project type; исправляемое отправление сохраняет версию исходной анкеты.
3. **Поля анкеты.** Во всех типах обязательны `goal`, `target_audience`, `expected_result`, непустой `functional_scope` и `has_integrations`. Если `has_integrations=true`, обязателен непустой `integrations`; если `false`, хранится пустой список. Необязательны `constraints`, `deadline`, `budget_min`, `budget_max`, `currency`; валюта обязательна, если задана любая сумма, а `budget_min <= budget_max`.
4. **Типовые ветви.** `website`: `has_existing_site`; при `true` обязателен HTTP(S) `existing_site_url`. `telegram_bot`: `has_existing_bot`; при `true` обязателен HTTP(S) `existing_bot_url`. `automation`: обязательный `trigger_type` из `scheduled|event|manual`; для `scheduled` требуется `schedule_details`, для `event` — `event_source`. `other`: обязательный `project_area` с описанием области проекта.
5. **Явный mapping анкеты → паспорт.** `goal` → `ProjectPassport.goal`; `target_audience` → `target_audience`; `expected_result` → `expected_result`; `functional_scope` → ключ project type в JSON `functional_scope`; `integrations` → ключ project type в JSON `integrations` со значением `{enabled, items}`; `constraints` → ключ project type в JSON `constraints`; `deadline`, `budget_min`, `budget_max`, `currency` → одноимённые поля. Ответы типа проекта сохраняются под `additional_data.questionnaire[project_type]` вместе с `schema_version`. Пустые необязательные ответы не очищают паспорт. Контрольные ответы `has_integrations` и `has_existing_*` сами по себе в паспорт не переносятся.
6. **Конфликты анкеты.** Пустое поле паспорта заполняется из анкеты; эквивалентное значение не меняется. Отличающееся непустое значение сохраняется вместе с ответом в `QuestionnaireConflict`, а паспорт остаётся неизменным. Очередь конфликтов видит только исполнитель. Он выбирает `keep_passport` или `apply_answer`; второе вызывает только `projects.services.update_passport` с текущей версией. Никакого автоматического создания общего `ProjectConflict` нет.
7. **Коррекции.** Запрос исполнителя меняет статус исходной отправки `submitted→correction_requested` (её ответы остаются неизменными) и создаёт новый `draft` с `supersedes_id`, копируя ответы для повторной проверки. Повтор запроса возвращает уже созданный черновик. Заказчик может менять только черновик; он подтверждает и отправляет его отдельно.
8. **Project State.** Переходы перечислены полностью; статус вне списка отклоняется как конфликт состояния (`409`). Конечные `completed`, `cancelled`, `rejected`, `resolved`, `dismissed` терминальны.

| Сущность | Статусы и разрешённые переходы |
|---|---|
| `ProjectStage` | `planned → active, cancelled`; `active → blocked, completed, cancelled`; `blocked → active, cancelled` |
| `Requirement` | `draft → confirmed, rejected`; `confirmed → in_progress, rejected`; `in_progress → blocked, completed, rejected`; `blocked → in_progress, rejected` |
| `Task` | `todo → in_progress, cancelled`; `in_progress → blocked, done, cancelled`; `blocked → in_progress, cancelled` |
| `OpenQuestion` | `open → resolved, dismissed` |
| `ProjectConflict` | `unresolved → resolved, dismissed` |

9. **Evidence.** В Stage 06 Evidence создаёт только исполнитель. Поддержаны ссылки на сообщения и ответы анкеты того же проекта; сервис проверяет проект источника и сохраняет snapshot excerpt/metadata. Связь с общим конфликтом неизменяема. Решение конфликта фиксирует actor, время, решение и запись `ProjectAuditLog`; resolved/dismissed не переоткрывается.
10. **Чат.** Сообщение — непустой текст до 10 000 символов. История — cursor pagination по 50 (максимум 100), стабильная сортировка `created_at, id`; отправка доступна участникам только в `active`, история читается и в read-only статусах. 60 сообщений/минуту/пользователь через REST и WebSocket. Повтор `client_message_id` с тем же текстом возвращает то же сообщение без нового события; другой текст с тем же ID даёт `409`.
11. **Документы.** Точный предел — `20 × 1024 × 1024` байта. Поддерживаются `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`, только при согласованности расширения и обнаруженного содержимого. PDF проверяется сигнатурой, DOCX — ZIP-контейнером и обязательными частями OOXML, TXT/Markdown — допустимым текстовым содержимым. Исходное имя хранится только как display metadata; storage key генерируется сервером.
12. **Жизненный цикл документов.** Архив требует двух согласий; до второго решения файл остаётся активным с состоянием `archive_pending`; отказ оставляет `active`. После обоих согласий — `archived`, файл сохраняется, его можно восстановить. Запрос permanent-delete возможен только для `archived`; оба участника явно согласны. 30 суток отмены начинаются со второго согласия; отмена возвращает в `archived`, затем восстановление — отдельное действие. Celery Beat проверяет due requests каждые 5 минут; задача идемпотентно удаляет source и существующие Stage 08 derivatives, если deadline прошёл и запрос не отменён. Stage 09 должен расширить cleanup для будущих chunks/embeddings до включения extraction. На backup-копии срока не обещаем.
13. **Листы и границы.** Проектные списки приглашений, Project State и документов — page pagination default 20/max 100, stable order. Чат — cursor pagination. Обмен сообщениями, документы и Project State доступны только при активном членстве в конкретном проекте; completed/archived проекты read-only. Completion percentage нет. Текстовый extraction, OCR, chunks и embeddings принадлежат Stage 09; malware scanner остаётся production gate.

## 4. Детальное поведение по этапам

### 4.1 Stage 04 — приглашения

- `ProjectInvitation` хранит project, creator, normalized email, `token_hash`, `status` (`pending|accepted|revoked|expired`), `expires_at`, accepter и timestamps. Один активный invitation на project/email. Уникальность customer membership остаётся также ограничена существующим DB constraint в `projects`.
- Raw invitation token is included only in the outbound email link; the create API response never returns it. The token is stored as a hash and never logged.
- REST: `GET/POST /api/v1/projects/{project_id}/invitations/`; `POST .../{invitation_id}/revoke/`; public throttled `POST /api/v1/invitations/preview/`; authenticated+verified throttled `POST /api/v1/invitations/accept/`. Небезопасные browser-запросы используют существующую CSRF/session-auth.
- Preview до валидации показывает только generic invalid response. Для валидного токена возвращает безопасный набор: project name, masked email hint, expiry, status; без project description/member list. Невалидный токен — `404`; известный просроченный/отозванный — `410` с безопасным кодом состояния. Email mismatch — `403`, без вывода полного приглашённого адреса.
- Create/revoke доступны только executor на `draft|active`. Accept доступен только matching verified user на `draft|active`. `draft→active`, customer membership и invitation `accepted` фиксируются одной транзакцией через владельца домена `projects`; `active` остаётся `active`. Completed/archived запрещают create/revoke/accept. Успешный повтор того же принятого пользователем токена возвращает тот же результат, не создавая membership или событие повторно.
- Письмо формируется Django email backend, ссылка использует `FRONTEND_BASE_URL` и fragment `#token=…`, чтобы token не попадал в HTTP request URL. Landing page читает token один раз, удаляет fragment из адресной строки и отправляет его только в POST body. Token не хранится в local/session storage. Неавторизованный участник переходит к login/register; невыполненная email verification объясняется, после неё приглашение можно открыть повторно.
- Frontend показывает форму приглашения и список со статусом; публичную landing/preview; вход/регистрацию; mismatch, invalid, expired, revoked, accepted и retry/error состояния; после принятия ведёт заказчика в нужный project.

### 4.2 Stage 05 — анкета

- Схемы размещены в backend repository как четыре JSON файла версии 1. Каждая схема имеет project type, version, `questions`, `required`, field type, deterministic `visible_if` branch, validation, and mapping key. Backend выбирает schema по project type из `projects` и является единственным источником валидации.
- `QuestionnaireSubmission` связывает проект, `schema_key/version`, статус, автора, отправителя, время и `supersedes_id`. `QuestionnaireAnswer` уникален по submission/question key и хранит JSON value, `origin=prefilled|customer`, confirmation и автора изменений. `QuestionnaireConflict` содержит answer ref, mapped passport field, snapshots обоих values, pending/resolution state, reviewer и timestamps. Schema JSON не хранится редактируемо в DB.
- Start pre-fills только те mapping keys, что уже есть в паспорте; источник помечается `prefilled` и пользователь должен подтвердить его перед submit. Редактирование меняет origin на `customer`. Неактивные branch keys запрещены и не сохраняются. Draft upsert доступен только customer этого проекта и только в `active`; submit валидирует сервером, подтверждает применимые ответы и блокирует отправление.
- Executor может увидеть submission status и очередь pending conflicts, затем запросить correction. Клиент редактирует только superseding draft. История предыдущих submitted rows/answers не обновляется и не удаляется.
- Submit и паспортные изменения атомарны. Сопоставления сгруппированы по passport field: различающиеся значения одного JSON-поля рассматриваются как конфликт, поле не обновляется частично. Запись применённых непустых non-conflicting mapping values выполняется через owner-service `projects.services.apply_questionnaire_mapping(*, project_id, actor, expected_version, mapped_changes)`. Она разрешает только verified customer submission mapping, повторно проверяет membership/status и сохраняет version/audit; это не прямой customer PATCH. Исполнительские конфликтные решения используют `projects.services.update_passport`. Stale version откатывает submit transaction и возвращает `409`, черновик остаётся редактируемым.
- Executor review UI может оставить passport value или применить submitted answer; разрешение также транзакционно и версионно. Заказчик видит собственную анкету и её статус, но не executor-only conflict queue.
- REST: `GET /api/v1/projects/{project_id}/questionnaire/`; `POST .../questionnaire/submissions/`; `PATCH /api/v1/questionnaire/submissions/{submission_id}/answers/`; `POST .../{submission_id}/submit/`; `POST .../{submission_id}/request-correction/`; отдельное executor-only action для resolution. Все project reads/mutations проверяют активное membership и роль.

### 4.3 Stage 06 — Project State

- `project_state` владеет `ProjectStage`, `Requirement`, `Task`, `OpenQuestion`, `ProjectConflict`, `Evidence` и link таблицами. Используются UUID, проектные FK/индексы, actor/timestamps, явные status choices. Процентных полей нет.
- `Evidence.source_type` in this scope is `questionnaire_answer|message`; each source is resolved by its owning app selector and checked against the project. Stage 06 implements and tests the questionnaire-answer resolver; Stage 07 adds the chat Message resolver after the chat model and selector exist. Evidence snapshots and conflict links are immutable. Participants see conflict values and sources; internal AIAnalysisRun and AIProposal never enter shared serializers or the aggregate.
- Read selector всегда ограничен active membership конкретного project; project member видит все shared entities во всех статусах проекта. Write service допускает только executor и project status `draft|active`. Customer API write отвечает `403`; неизвестный/cross-project ID отвечает безопасным `404`.
- Статус меняется только через service transition validator. Обычный PATCH полей не может переопределить терминальный статус или переход вне таблицы §3. Изменения и audit row совершаются транзакционно. Conflict resolution сохраняет actor, timestamp и resolution text; terminal conflicts нельзя редактировать повторно.
- API contract: aggregate `GET /api/v1/projects/{project_id}/state/` возвращает counts + ссылки на scoped collections, а не неограниченную историю; отдельные GET/POST/PATCH коллекции из API contract используют page pagination. Добавляется `POST /api/v1/projects/{project_id}/conflicts/` для executor-created conflict с минимум двумя same-project evidence refs; PATCH остаётся только для разрешения pending conflict.
- Frontend: общий State view с этапами, требованиями, задачами, открытыми вопросами и конфликтами. Executor controls доступны по роли и backend-ошибка всё равно отображается. Customer может открыть каждую shared запись, но controls отсутствуют. Empty state предлагает executor создать первую запись, а заказчику объясняет, что план ещё не добавлен. Дата/status видны; процента, Gantt и аналитики нет.

### 4.4 Stage 07 — чат

- `chat.Message` принадлежит только app `chat`; sender — active project member. REST владеет записи/history; Channels отправляет исключительно `message.created` в group одного project.
- REST: `GET/POST /api/v1/projects/{project_id}/messages/`, cursor pagination, стабильный обратный курсор для старых записей. POST принимает `content` + UUID `client_message_id`. Constraint уникален по project/sender/client ID. Тот же ID и тот же normalized content возвращает прежнее сообщение; тот же ID с другим content — `409`.
- Сервис сначала транзакционно сохраняет сообщение, затем публикует group event только через `transaction.on_commit`. На дубле событие не повторяется. WebSocket `/ws/v1/projects/{project_id}/chat/` использует Django session cookie, проверяет auth+active membership на соединении и присоединяет только к project-specific group. Неавторизованный запрос не подключается. REST history восстанавливает пропуски; повторная доставка дедуплицируется `message.id`.
- Project chat WebSocket handshake допускает только `Origin` из `FRONTEND_BASE_URL` или `CSRF_TRUSTED_ORIGINS`; отсутствующий или чужой origin отклоняется до session/member authorization. Отдельный `/ws/v1/health/` остаётся без Origin-проверки.
- Message submission is REST-only (`POST /api/v1/projects/{project_id}/messages/`); it is allowed only for an `active` project, while history remains available in read-only statuses. New REST submissions are limited to 60 per user per fixed UTC minute and return `429`; idempotent replays do not count. WebSocket is delivery-only and has no client-to-server message submission or separate send-limit close flow. This clarifies ADR-005, the Stage 07 brief, and R102i, as discovered in T08.
- UI показывает страницы истории в хронологическом порядке, optimistic message с `sending/sent/failed`, повтор отправки использует исходный `client_message_id`. На reconnect frontend повторно загружает latest REST history; duplicate events не создают повторные строки.

### 4.5 Stage 08 — документы

- `documents` владеет metadata, `DocumentLifecycleRequest`, `DocumentLifecycleApproval`, storage service, selectors, API и периодической deletion task. File bytes лежат в Django default storage на persistent `MEDIA_ROOT` (Compose volume `/app/media`); Postgres хранит metadata и generated `storage_key`, не file bytes.
- Upload (`multipart/form-data`) доступен активному члену проекта на `draft|active`; сервер отвергает размер свыше 20 MiB (`413`) и несогласованные/неподдерживаемые extension/content (`415`). PDF должен иметь PDF signature; DOCX — ZIP с `[Content_Types].xml` и `word/document.xml`; TXT/Markdown — валидное текстовое содержимое без запрещённых бинарных bytes. Нулевой TXT/Markdown принимается как пустой текстовый файл, поскольку minimum size не задан; его processing status остаётся `queued` до Stage 09. Client MIME не считается доказательством. Storage key UUID-based, basename display filename не используется как путь. SHA-256 вычисляется на сервере. Если запись metadata не удалась после storage save, файл удаляется компенсирующим действием.
- Download выполняется только авторизованным active member через backend `FileResponse` как attachment, с безопасным basename и `X-Content-Type-Options: nosniff`. File bytes не доступны по public URL. Любой ID без membership маскируется как `404`.
- `GET /api/v1/projects/{project_id}/documents/` по умолчанию перечисляет `active|archive_pending`; `?status=archived` перечисляет архив; отдельное представление `deletion_pending` позволяет обоим участникам отменить ожидание. `deleted` не возвращается как содержимое. Archived/deletion-pending сразу исключены из активного списка и retrieval selector.
- Lifecycle request хранит action, initiator и status; initiator approval создаётся одновременно с запросом. Другой participant может approve/reject. Archive: `active→archive_pending→archived`; архивный файл и future derived data не удаляются и могут быть восстановлены любым участником, пока project разрешает mutations. Rejection/cancellation archive request оставляет документ active.
- Восстановление `archived` документа при `pending` permanent-delete request с единственным approval инициатора атомарно отменяет этот незавершённый request и аудирует обе операции. Если оба участника уже одобрили удаление и документ находится в `deletion_pending`, сначала требуется явная отмена удаления.
- Permanent delete: только из `archived`; после второго approval файл становится `deletion_pending`, записывается `deletion_after=now()+30d`; Celery Beat проверяет сроки каждые 5 минут. Любой participant может cancel до deadline; это переводит request в cancelled, document возвращается в `archived`, deletion job становится no-op. По истечении периода task идемпотентно удаляет source file и имеющиеся Stage 08 derived rows/files, очищает content-bearing metadata, помечает document `deleted` и оставляет только минимальную audit запись. Stage 09 должен добавить cleanup будущих chunks/embeddings до включения extraction.
- В API добавляются status query для активной/архивной/ожидающей удаления коллекции; уже задокументированные create/approve/reject/cancel/restore endpoints сохраняются. Новые lifecycle requests, approve/reject и restore требуют active membership и mutable parent project (`draft|active`). Любой active member может отменить ожидающее удаление до deadline даже после закрытия parent project, потому что это отзыв ранее данного согласия. Пятиминутный sweep выполняет уже одобренное удаление по истечении окна независимо от более позднего project status; иначе подтверждённый deletion request мог бы зависнуть.
- UI: shared list, active/archive views, upload with max/type validation, status/details, download, archive request, approve/reject, restore, deletion request, approval and cancel countdown. Copy явно показывает 30-дневную отмену и то, что это не гарантия немедленного удаления из резервных копий. Scanned PDF/OCR и настоящий parser не реализуются; валидный файл отображается с processing status `queued` до Stage 09.

## 5. Cross-cutting API, permissions и ошибки

- Все REST endpoints используют существующие session cookies, `CsrfSanitizingAPIView`/shared API error envelope и OpenAPI. Небезопасные requests требуют CSRF. Client request/response types генерируются из live schema; generated types вручную не править.
- API остаётся source of truth. Сервис владельца app проверяет все инварианты; serializer проверяет форму payload, но не подменяет business service. Cross-project resources не раскрывают данные: project-scoped IDs не находятся через active member selectors.
- Use `ProjectAuditLog` для security-relevant invite, membership, questionnaire resolution, State transition, chat submission (если только ID/action), upload/download where useful, lifecycle action. Audit allowlist расширяется только безопасными полями: actor, target IDs, status transitions, changed field names, decision kind, versions. Raw tokens, email body, message/file contents, passwords и provider secrets не записывать.
- Ошибки используют существующий envelope. `400` — malformed/field validation, `401` — no session, `403` — role/CSRF, `404` — inaccessible project/resource or unknown invitation token, `409` — version/status/idempotency collision, `410` — известный expired/revoked invite, `413` — file too large, `415` — unsupported/mismatched file, `429` — rate limit. Backend detail не включает stack traces, raw tokens, invitation email или storage path.
- UI у каждого нового data view имеет loading, empty, recoverable error/retry, invalid input, permission or lifecycle state. Unsaved questionnaire draft is retained on API/network validation errors. Message failed state preserves text and id for retry. File upload failure cleans up partial storage when possible and lets the user retry.

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

## 7. Доведение среды и проверка

- Create additive Django migrations; do not edit Stage01–03 migrations or erase local volumes/data.
- Because Stage 08 introduces a real due-time task, add a single Celery Beat service with a five-minute idempotent sweep. Keep it absent from any domain tests where not needed; worker and Beat use the existing Redis URL.
- After backend changes rebuild backend and migrate. Run backend format/lint, `makemigrations --check`, schema validation, and the full pytest suite. For clean DB verification use a separate disposable PostgreSQL database, never `down -v` on the user’s data.
- After API changes regenerate TypeScript types from running backend and copy generated schema to source. Run frontend formatting/lint/typecheck/tests/build. Recreate frontend after code changes before live browser checks.
- Stage boundary: commit every reviewed ticket separately, then run the acceptance checks for its numbered stage. After the final ticket in each stage 04-08 is committed, push that stage's commits to the configured upstream `main`. This checkout has no Git remote, so attempt the required push after each stage, record the exact failure, keep local commits on `main`, and never invent a remote URL.

## 8. Вне рамок

| Требование | Почему не сейчас |
|---|---|
| R70–R75 — chat attachments, editing/deletion, read receipts, typing indicators, group chat, voice/video | Explicitly excluded by Stage 07; simple one-to-one text chat is sufficient. |
| R99 — full-text extraction and embeddings | Stage 09 owns parsers, chunks, vectors and retrieval. Scanned-PDF UX is not required before that pipeline exists. |
| malware scanning | No scanner is selected or available; record a production-readiness gate, do not claim uploads are scanned. |
| password reset, account deletion, AI analyses/proposals, specification generation, public-order import, OCR, audio/video processing, private documents, completion percentages, microservices | Existing product/architecture scope excludes these; no new capability is added by this flight. |

## 9. Открытые места

Нет placeholders по текущим этапам. Production malware scanning остаётся отдельным release gate. Решение по scanned-PDF processing передано Stage 09; implementation now accepts only valid PDF containers and does not claim they have extractable text.

## 10. Requirement coverage

| Requirement | Spec sections |
|---|---|
| R01 | 4.1, 5 |
| R02 | 4.1, 5 |
| R03 | 4.1, 5 |
| R04 | 4.1, 5 |
| R05 | 4.1, 5 |
| R06 | 4.1, 5 |
| R07 | 4.1, 5 |
| R08 | 4.1, 5 |
| R09 | 4.1, 5 |
| R10 | 4.1, 5 |
| R11 | 4.1, 5 |
| R12 | 4.1, 5 |
| R13 | 4.1, 5 |
| R14 | 4.1, 5 |
| R15 | 4.1, 5 |
| R16 | 4.1, 5 |
| R17 | 4.1, 5 |
| R18 | 4.1, 5 |
| R19 | 4.1, 5 |
| R20 | 4.1, 5 |
| R21 | 4.1, 5 |
| R22 | 3, 4.2, 5 |
| R23 | 3, 4.2, 5 |
| R24 | 3, 4.2, 5 |
| R25 | 3, 4.2, 5 |
| R26 | 3, 4.2, 5 |
| R27 | 3, 4.2, 5 |
| R28 | 3, 4.2, 5 |
| R29 | 3, 4.2, 5 |
| R30 | 3, 4.2, 5 |
| R31 | 3, 4.2, 5 |
| R32 | 3, 4.2, 5 |
| R33 | 3, 4.2, 5 |
| R34 | 3, 4.2, 5 |
| R35 | 3, 4.2, 5 |
| R36 | 3, 4.2, 5 |
| R37 | 3, 4.2, 5 |
| R38 | 3, 4.2, 5 |
| R39 | 3, 4.2, 5 |
| R40 | 3, 4.2, 5 |
| R41 | 3, 4.3, 5 |
| R42 | 3, 4.3, 5 |
| R43 | 3, 4.3, 5 |
| R44 | 3, 4.3, 5 |
| R45 | 3, 4.3, 5 |
| R46 | 3, 4.3, 5 |
| R47 | 3, 4.3, 5 |
| R48 | 3, 4.3, 5 |
| R49 | 3, 4.3, 5 |
| R50 | 3, 4.3, 5 |
| R51 | 3, 4.3, 5 |
| R52 | 3, 4.3, 5 |
| R53 | 3, 4.3, 5 |
| R54 | 3, 4.3, 5 |
| R55 | 3, 4.3, 5 |
| R56 | 3, 4.3, 5 |
| R57 | 3, 4.3, 5 |
| R58 | 3, 4.3, 5 |
| R59 | 3, 4.4, 5 |
| R60 | 3, 4.4, 5 |
| R61 | 3, 4.4, 5 |
| R62 | 3, 4.4, 5 |
| R63 | 3, 4.4, 5 |
| R64 | 3, 4.4, 5 |
| R65 | 3, 4.4, 5 |
| R66 | 3, 4.4, 5 |
| R67 | 3, 4.4, 5 |
| R68 | 3, 4.4, 5 |
| R69 | 3, 4.4, 5 |
| R70 | 8 |
| R71 | 8 |
| R72 | 8 |
| R73 | 8 |
| R74 | 8 |
| R75 | 8 |
| R76 | 3, 4.5, 5, 7 |
| R77 | 3, 4.5, 5, 7 |
| R78 | 3, 4.5, 5, 7 |
| R79 | 3, 4.5, 5, 7 |
| R80 | 3, 4.5, 5, 7 |
| R81 | 3, 4.5, 5, 7 |
| R82 | 3, 4.5, 5, 7 |
| R83 | 3, 4.5, 5, 7 |
| R84 | 3, 4.5, 5, 7 |
| R85 | 3, 4.5, 5, 7 |
| R86 | 3, 4.5, 5, 7 |
| R87 | 3, 4.5, 5, 7 |
| R88 | 3, 4.5, 5, 7 |
| R89 | 3, 4.5, 5, 7 |
| R90 | 3, 4.5, 5, 7 |
| R91 | 3, 4.5, 5, 7 |
| R92 | 3, 4.5, 5, 7 |
| R93 | 3, 4.5, 5, 7 |
| R94 | 3, 4.5, 5, 7 |
| R95 | 3, 4.5, 5, 7 |
| R96 | 3, 4.5, 5, 7 |
| R97 | 3, 4.5, 5, 7 |
| R98 | 3, 4.5, 5, 7 |
| R99 | 8, 9 |
| R100i | 2, 5, 7 |
| R101i | 2, 5, 7 |
| R102i | 2, 5, 7 |

All 102 manifest requirements have a spec location; R70-R75 and R99 are explicitly deferred.
