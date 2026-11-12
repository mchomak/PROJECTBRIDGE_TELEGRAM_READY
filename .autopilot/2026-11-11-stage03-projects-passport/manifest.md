# Stage 03 — Requirements Manifest

Source: `2026-11-11-brief.md`. Only the user may remove a requirement.

| ID | From the brief (verbatim) | Status | Reason | Where |
|---|---|---|---|---|
| R01 | “Allow an authenticated executor to create and manage a project and its initial passport.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 01?04 |
| R02 | “Read first”; `AGENTS.md`; `docs/product/MVP_SCOPE.md`; `docs/database/DATA_MODEL.md`; `docs/api/API_CONTRACT.md`; `docs/security/ACCESS_CONTROL_AND_SECURITY.md`; `docs/architecture/FRONTEND_ARCHITECTURE.md` | done | Required source documents read before coding. | — |
| R03 | “Stage 02.” | done | Stage 02 is present and marked complete in the run register. | — |
| R04 | “Implement Project, ProjectMember, and ProjectPassport models and migrations.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R05 | “Support the four initial project types only: `website`, `telegram_bot`, `automation`, `other`.” | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R06 | “Enforce one active executor and one active customer per project.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R07 | “Create Project, executor membership, and passport atomically.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R08 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `project list` | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Tickets: 02, 03 |
| R09 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `create` | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R10 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `detail` | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R11 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `update` | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R12 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `member list` | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R13 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `complete` | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R14 | “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.” — `archive` | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R15 | “Implement passport read and executor update.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R16 | “Add passport `version` handling and return `409 Conflict` for stale updates.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R17 | “Ensure all project reads and writes are scoped to active project membership and role.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Tickets: 02, 03 |
| R18 | “Project list page.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R19 | “Project creation flow with the four project types.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R20 | “Project overview page.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R21 | “Passport view/edit experience for executor.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R22 | “Read-only passport view for customer once a customer membership exists.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R23 | “Loading, empty, validation, and error states.” — `Loading` | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R24 | “Loading, empty, validation, and error states.” — `empty` | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R25 | “Loading, empty, validation, and error states.” — `validation` | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R26 | “Loading, empty, validation, and error states.” — `error states` | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R27 | “Customer invitation flow.” | deferred | Explicitly listed out of scope for Stage 03 |Out of scope: R27 in spec.md|
| R28 | “Questionnaire and passport auto-population.” | deferred | Explicitly listed out of scope for Stage 03 |Out of scope: R28 in spec.md|
| R29 | “Project State entities.” | deferred | Explicitly listed out of scope for Stage 03 |Out of scope: R29 in spec.md|
| R30 | “Progress percentages.” | deferred | Explicitly listed out of scope for Stage 03 |Out of scope: R30 in spec.md|
| R31 | “Public freelance-order import.” | deferred | Explicitly listed out of scope for Stage 03 |Out of scope: R31 in spec.md|
| R32 | “Project and membership models.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R33 | “ProjectPassport model and service layer.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R34 | “Project and passport API endpoints.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Tickets: 02, 03 |
| R35 | “Project list/create/detail UI.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Ticket 04 |
| R36 | “Permission and concurrency tests.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R37 | “A verified authenticated user can create a project.” | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R38 | “Project, executor membership, and passport are created in one transaction.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R39 | “Only the four agreed project types are accepted.” | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R40 | “A user sees only projects where they are an active member.” | done | Ticket 02 implementation and independent review passed; 18 focused and 72 full backend tests passed. | Ticket 02 |
| R41 | “Only the executor can update project metadata and passport directly.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Tickets: 02, 03 |
| R42 | “Both project participants can read the passport.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R43 | “A stale passport update returns `409 Conflict` and does not overwrite newer data.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| R44 | “Duplicate active executor/customer memberships are prevented.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R45 | “Tests cover cross-project access and role violations.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Tickets: 02, 03 |
| R46 | “The exact passport field set must follow `DATA_MODEL.md` and the questionnaire mapping decisions.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R47 | “If the current product document defines different required fields, surface the discrepancy instead of silently adding/removing fields.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| R48 | “Implement Stage 03 only. Build the project and passport vertical slice, including UI, API, migrations, permissions, and tests.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 01?04 |
| G01 | “Используем четыре статуса: `draft`, `active`, `completed`, `archived`.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| G02 | “`draft → active` — после принятия приглашения заказчиком.” | deferred | Accepted product decision; Stage 04 invitation acceptance owns this transition; Stage 03 implements no invitation or customer-membership workflow. |Out of scope: G02 in spec.md|
| G03 | “`active → completed` — исполнитель завершает проект.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 03, 04 |
| G04 | “`completed → active` — исполнитель может повторно открыть проект.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 03, 04 |
| G05 | “`draft / active / completed → archived` — исполнитель может архивировать проект.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 03, 04 |
| G06 | “`archived → previous_status` — исполнитель может восстановить проект в том статусе, в котором он находился до архивирования.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 03, 04 |
| G07 | “Для восстановления необходимо сохранять предыдущий статус проекта. Можно добавить поле `status_before_archive` в модель Project. После восстановления оно очищается.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G08 | “Изменять статус проекта может только исполнитель.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G09 | “Оба участника сохраняют доступ ко всем данным проекта на чтение.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G10 | “История чата доступна для просмотра, отправка новых сообщений запрещена.” | deferred | Accepted policy for its owning future subsystem; implementation is outside Stage 03. |Out of scope: G10 in spec.md|
| G11 | “Документы можно просматривать и скачивать, загружать новые нельзя.” | deferred | Accepted policy for its owning future subsystem; implementation is outside Stage 03. |Out of scope: G11 in spec.md|
| G12 | “Project State доступен на чтение, изменения запрещены.” | deferred | Accepted policy for its owning future subsystem; implementation is outside Stage 03. |Out of scope: G12 in spec.md|
| G13 | “Новые ответы на анкету не принимаются.” | deferred | Accepted policy for its owning future subsystem; implementation is outside Stage 03. |Out of scope: G13 in spec.md|
| G14 | “Проект скрывается из основного списка и отображается в отдельном разделе архивных проектов.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 02, 04 |
| G15 | “Оба участника сохраняют доступ ко всем существующим данным на чтение.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 02?04 |
| G16 | “Все операции изменения данных заблокированы.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G17 | “Архивирование не означает удаление проекта или его документов.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G18 | “Пока не реализуем автоматическое удаление завершённых или архивных проектов.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G19 | “Сроки хранения 12 месяцев и 14 дней не считаем утверждёнными продуктовыми требованиями.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G20 | “Не добавляем самостоятельно новые бизнес-поля.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G21 | “Не определяем дополнительные обязательные поля.” | done | Ticket 03 implementation passed independent review; 39 project tests and 90 full backend tests passed. | Ticket 03 |
| G22 | “`draft` — исполнитель создал проект, заполняет паспорт и готовит его к работе.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| G23 | “`active` — полноценная работа над проектом.” | done |Ticket 01 implementation and review passed; full backend suite is green. |Ticket 01|
| G24 | “Сначала заверши синхронизацию документации, затем продолжай брифинг и реализацию Stage 03.” | done |Documentation prerequisite completed before Phase 3/specification and implementation resumed. |Docs synchronized before continuing Stage 03|
| G25 | “Не меняй существующий код и ранее созданные материалы прогона без необходимости.” | done | Ticket 04 implementation and independent reviews passed; 29 frontend and 91 backend tests passed. | Tickets: 01?04 |

## Phase 2 resolution

The project owner’s 2026-11-11 addendum is recorded verbatim under `## Дополнения` in the brief. It resolves the project lifecycle and archive access rules. G01–G25 capture its new or clarified requirements, including the documentation prerequisite and change-discipline constraint. The 12-month project-retention and 14-day backup periods are explicitly not approved product requirements. Questionnaire mappings and questionnaire requiredness remain Stage 05 decisions; Stage 03 uses the exact `ProjectPassport` fields and types now approved in `DATA_MODEL.md`.

G1 passed after the owner-approved addendum; G2 is being completed against the specification. R27–R31 and G02, G10–G13 remain deferred to Stage 04 or their owning subsystem stages; all other manifest rows are mapped to the specification.
