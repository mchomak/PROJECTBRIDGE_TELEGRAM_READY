# Спецификация: Stage 03 — Projects and Project Passport

## Задача

Исполнитель должен завести проект, подготовить его паспорт и видеть все
свои проекты. После появления заказчика оба участника должны видеть
общий паспорт и данные проекта, а статус проекта должен управлять тем,
какие действия доступны.

## Решение

В защищённом приложении появятся список обычных проектов, отдельный
архив, форма создания и страница проекта с паспортом. Новый проект
создаётся как черновик вместе с активным членством исполнителя и пустым
паспортом. Исполнитель может менять описание проекта и паспорт, завершать,
повторно открывать, архивировать и восстанавливать проект согласно его
состоянию. Все участники читают паспорт и данные проекта; в завершённых и
архивных проектах записи недоступны для изменения. API проверяет каждое
действие независимо от интерфейса.

**Плановый ярус:** T2, потому что один вертикальный срез пересекает
database/domain, REST/OpenAPI, audit и React/FSD frontend; каждый слой
имеет собственные acceptance tests.

## Пользовательские истории

| # | Метка | История | Приёмка |
|---:|:---|:---|:---|
| 1 | R01, R04, R07, R09, R32, R37, R38 | Как подтверждённый исполнитель, я создаю проект с паспортом, чтобы начать его подготовку. | Project со статусом `draft`, активное членство executor и ProjectPassport создаются атомарно; сбой любой части откатывает всё. Неподтверждённая или анонимная сессия не создаёт данных. После 201 UI открывает обзор созданного проекта. |
| 2 | R05, R19, R39 | Как исполнитель, я выбираю один из четырёх типов проекта. | Принимаются только `website`, `telegram_bot`, `automation`, `other`; другое значение возвращает field validation error. |
| 3 | R18, R23, R24, R26, R35 | Как исполнитель, я вижу свои обычные проекты и могу открыть архив. | Список включает проекты с активным членством, исключает `archived`; `?status=archived` возвращает только архив. Пустые списки объясняют, как создать проект или вернуться к обычным проектам. Ошибка загрузки оставляет возможность повторить запрос. |
| 4 | R10, R17, R20, R40 | Как активный участник, я открываю проект и его участников. | Участник с активным членством читает проект, активный список участников и паспорт в любом статусе. Пользователь без активного членства не получает данные чужого проекта. |
| 5 | R11, R25, R41 | Как исполнитель, я обновляю название, тип или описание проекта, пока проект готовится или активен. | Метаданные принимаются только в `draft` и `active`; ошибки валидации привязаны к полям и не теряют введённые значения. Статус и `status_before_archive` нельзя передать как редактируемые поля. |
| 6 | R12, R44 | Как участник, я вижу текущих участников проекта. | Список содержит только активные членства; БД не допускает более одного активного участника каждой роли и дубли членства пользователя в том же проекте. |
| 6a | R06.1 | Как система, я сохраняю непротиворечивое членство пользователя в проекте. | Есть не более одной строки membership на `(project, user)`; роли `executor`/`customer`, статусы `active`/`left`/`revoked`; только `active` даёт доступ. Это уточнение следует модели данных. |
| 7 | R13, G03 | Как исполнитель, я завершаю активный проект. | Только исполнитель переводит `active` в `completed`; недопустимое исходное состояние возвращает `409`. |
| 7a | R13.1 | Как участник, я вижу время последнего завершения проекта. | При переходе в `completed` устанавливается `completed_at`; reopen его сохраняет, а повторное завершение обновляет. Это техническая трактовка nullable completion timestamp из модели данных. |
| 8 | G04 | Как исполнитель, я повторно открываю завершённый проект. | Только исполнитель переводит `completed` в `active`; прочие переходы через этот action возвращают `409`. |
| 9 | R14, G05, G07, G14, G16, G17, G18 | Как исполнитель, я архивирую проект и позже восстанавливаю его. | Архивирование из `draft`, `active` или `completed` сохраняет исходный статус в `status_before_archive`, проставляет `archived_at`, сохраняет участников и данные. Восстановление возвращает исходный статус, очищает `status_before_archive` и `archived_at`. Архив не удаляет данные; автоматическое удаление не планируется. |
| 9a | R14.1 | Как система, я сохраняю согласованность архивного состояния. | При `archived` `status_before_archive` и `archived_at` заданы; при восстановлении оба очищены. Это согласует lifecycle fields из модели данных с переходами G07. |
| 10 | G01, G03, G04, G05, G06, G07, G08, G22, G23 | Как участник, я полагаюсь на однозначное состояние проекта. | Допустимы только `draft`, `active`, `completed`, `archived` и описанные в модели переходы. Создание устанавливает `draft`; только исполнитель запускает Stage 03 lifecycle actions. `draft` → `active` применяется при приглашении заказчика в Stage 04. |
| 11 | R15, R21, R22, R33, R42, R46, R47 | Как исполнитель или заказчик, я читаю общий паспорт, а исполнитель редактирует его до завершения или архивации. | Обе роли с активным членством читают паспорт. Только executor обновляет его в `draft`/`active`; customer всегда read-only. Используются только поля и типы из `DATA_MODEL.md`, без дополнительных бизнес-полей и правил обязательности. |
| 12 | R16, R43 | Как исполнитель, я не затираю изменения паспорта, сделанные после загрузки моей формы. | `PATCH` требует текущую версию. Успех атомарно проверяет версию, сохраняет изменения и увеличивает её на 1; устаревшая версия возвращает `409 Conflict` и не меняет данные. После конфликта UI сообщает об обновлении и позволяет загрузить актуальный паспорт, сохраняя введённый текст до явного перезагрузки. |
| 13 | R23, R25, R26 | Как пользователь, я понимаю состояние загрузки, валидации и сетевой ошибки. | Страницы показывают загрузку, пустое состояние, field-level validation и retryable read errors. Неуспешная мутация не очищает форму; мутации не повторяются автоматически. |
| 14 | R36, R45 | Как владелец продукта, я могу проверить изоляцию и границы ролей. | Тесты покрывают подтверждённую/неподтверждённую сессию, executor/customer/неучастника, другой проект, все Stage 03 lifecycle transitions, ограничения членства, атомарный create и stale passport update без потери данных. Invitation-driven activation проверяется в Stage 04. |
| 15 | G09 | Как участник завершённого проекта, я продолжаю читать доступные данные проекта. | Project, members и passport API остаются доступны обоим активным участникам в `completed`; для passport и project metadata изменения запрещены. Доступ к чатам, документам, Project State и ответам анкеты сохраняется по этой же политике в соответствующих стадиях-владельцах. |
| 16 | G10, G11, G12, G13 | Как участник завершённого проекта, я читаю историю и существующие данные, но не создаю новые. | Политика read-only для чата, документов, Project State и анкеты зафиксирована для их собственных стадий; Stage 03 не добавляет эти подсистемы. |
| 17 | G15, G19 | Как участник архивного проекта, я читаю сохранённые данные, зная, что архивирование не означает удаление. | Проект доступен из архива обоим активным участникам; периодов автоудаления проекта 12 месяцев или хранения backup 14 дней нет. |
| 18 | G20, G21 | Как участник, я использую паспорт без скрытых полей и требований. | В паспорте есть ровно утверждённый набор; requiredness ответов и mapping questionnaire остаются решениями Stage 05. |
| 19 | R02, R03, R48 | Как владелец Stage 03, я получаю только согласованный вертикальный срез. | Реализация опирается на перечисленные документы и Stage 02, не включает приглашения, анкеты, Project State, прогресс или импорт заказов. |
| 20 | G24 | Как владелец продукта, я продолжаю Stage 03 только после фиксации правил в документации. | До спецификации и реализации синхронизируются `OPEN_DECISIONS.md`, `DATA_MODEL.md`, `API_CONTRACT.md`, `ACCESS_CONTROL_AND_SECURITY.md` и связанные stage criteria; состояния и операции согласованы. |
| 21 | G25 | Как владелец Stage 03, я сохраняю прежнюю работу, меняя только то, что нужно для этого этапа. | Нет несвязанных изменений существующего кода или ранее созданных материалов прогона; Stage 03 меняет только необходимые integration points и добавляет материалы текущего прогона. |
| 22 | R08.1 | Как пользователь, я нахожу проект в устойчивом списке даже при росте количества проектов. | Список использует page-number pagination с bounded page size и стабильным порядком. Endpoint-local defaults задокументированы ниже. |
| 23 | R09.1 | Как исполнитель, я могу исправить ошибочное название до создания проекта. | Название обязательно, пробелы по краям убираются, пустое или слишком длинное название возвращает field validation error без потери ввода. |
| 24 | R12.1 | Как участник, я понимаю, кто состоит в проекте. | Список активных участников возвращает display-safe профильные поля и роль; необязательные личные данные не раскрываются без нужды. |
| 25 | R15.1 | Как исполнитель, я сохраняю типизированные значения паспорта. | Поля проверяются по согласованным типам, включая длину currency; валидные данные не получают дополнительной доменной requiredness. |
| 26 | A01 → R17 | Как владелец продукта, я могу проверить важные изменения доступа и статуса проекта. | Security-relevant мутации записываются в `ProjectAuditLog` без значений паспорта или секретов. Дополнение следует обязательной security-документации; audit не получает отдельные API или UI. |

## Решения по реализации

### Модель и lifecycle

- `projects` владеет `Project`, `ProjectMember`, `ProjectPassport`, их
  ограничениями, selectors, services и REST API. В `Project` хранятся
  UUID, `name`, nullable `description`, `project_type`, `status`,
  `status_before_archive`, `created_by`, `created_at`, `updated_at`,
  nullable `completed_at` и nullable `archived_at`.
- Новые проекты создаются в `draft`. `ProjectMember` получает роль
  `executor` и `active` status. Membership statuses — `active`, `left`,
  `revoked`; только `active` даёт доступ. Customer membership не создаётся
  при обычном create в Stage 03.
- База данных ограничивает роли значениями `executor`/`customer`, статусы
  `active`/inactive values из модели, уникальность `(project, user)` и
  не более одного active member каждого role на проект. Условное
  ограничение связывает `archived` с непустыми `status_before_archive` и
  `archived_at`; для остальных статусов оба поля очищены. `status` и
  архивные поля изменяются только lifecycle services.
- Lifecycle services используют транзакцию и блокировку строки Project,
  затем проверяют исходный статус и роль до записи. Неподдерживаемый
  переход отвечает `409`. Повторное завершение после reopen устанавливает
  `completed_at` заново; reopen его не очищает. Restore очищает
  `archived_at` и `status_before_archive`.
- Invitation acceptance и создание customer membership принадлежат
  Stage 04. В Stage 03 нет invitation flow, customer-member creation или
  сервиса принятия приглашений. Stage 04 реализует project-owned mutation
  в своей invitation transaction; другое приложение не должно напрямую
  менять Project или ProjectMember.
- Read selectors всегда фильтруют Project по `ProjectMember.status=active`
  для пользователя. Запросы к существующему, но чужому проекту отвечают
  `404`; роль без нужного действия в доступном проекте — `403`.

### Passport

`ProjectPassport` — один-к-одному с Project, создаётся вместе с проектом,
имеет `version=1`, `created_at`, `updated_at` и ровно следующие поля из
`DATA_MODEL.md`: `goal` (text), `target_audience` (text),
`expected_result` (text), `functional_scope` (JSONB), `integrations`
(JSONB), `constraints` (JSONB), `deadline` (nullable date), `budget_min`
и `budget_max` (nullable decimal), `currency` (nullable 3-character
code), `additional_data` (JSONB). Внешний PATCH запрещает неизвестные
ключи и не принимает `project_id`, `version` для изменения, timestamps или
другие служебные поля. Все поля допускают отсутствие дополнительного
бизнес-requiredness; nullable поля хранят `null`, text поля — пустую
строку, JSONB создаются с пустым объектом `{}`. JSON содержимое не
получает доменной схемы в Stage 03.

PATCH должен передавать `version` и хотя бы одно поле паспорта. Обновление
одним compare-and-update действует по версии: на совпавшей версии
сохраняются только переданные поля и версия увеличивается; несовпавшая
версия приводит к 409 без записи. `version` не может быть изменён
клиентом. GET показывает паспорт всем активным участникам во всех
статусах проекта. PATCH требует executor membership и `draft`/`active`.

### API

Используется существующий REST `/api/v1/`, session authentication, CSRF
для мутаций и общий error envelope (`code`, `detail`, `errors`,
`request_id`). Список ресурсов пагинируется по страницам, 20 записей на
страницу и максимум 100; порядок `updated_at DESC, id ASC`. Эти пределы
локальны для project list и не задают глобальные DRF defaults.

| Method | Endpoint | Поведение |
|:--|:--|:--|
| GET, POST | `/api/v1/projects/` | Список своих неархивных проектов; создание для verified user. |
| GET, PATCH | `/api/v1/projects/{project_id}/` | Чтение активным участником; executor меняет metadata только в `draft`/`active`. |
| GET | `/api/v1/projects/{project_id}/members/` | Список активных участников проекта. |
| POST | `/api/v1/projects/{project_id}/complete/` | Executor: `active` → `completed`. |
| POST | `/api/v1/projects/{project_id}/reopen/` | Executor: `completed` → `active`. |
| POST | `/api/v1/projects/{project_id}/archive/` | Executor: `draft`/`active`/`completed` → `archived`. |
| POST | `/api/v1/projects/{project_id}/restore/` | Executor: `archived` → `status_before_archive`. |
| GET, PATCH | `/api/v1/projects/{project_id}/passport/` | Чтение участникам; update executor в `draft`/`active` с version. |

Обычный список не включает архивные проекты; `?status=archived` — только
архив. Другие значения `status` возвращают 400. Creation payload содержит
`name`, `project_type`, optional nullable `description`; server-controlled
поля игнорируются не молча, а отвергаются как неизвестные. Project PATCH
принимает только `name`, `project_type`, `description`; паспорт PATCH —
только business fields выше и текущий `version`. Мутации возвращают
обновлённый ресурс; создание — 201. Ошибки ввода — 400, отсутствие
сессии — 401, роль/верификация — 403, отсутствие членства/ресурса — 404,
устаревшая версия или запрещённый переход — 409.

`common.ProjectAuditLog` сохраняет security-relevant проектные мутации:
создание, изменение метаданных, переходы статуса, добавление customer
membership сервисом приглашений и обновление паспорта. Metadata содержит
только actor/target/action, названия изменённых полей и версии/статусы;
не значения паспорта, токены или иное содержимое проекта. Запись audit и
основная мутация транзакционны. Отдельного audit API/UI нет.

Project detail response содержит `id`, `name`, `description`,
`project_type`, `status`, `created_at`, `updated_at`, `completed_at` и
`archived_at`; не содержит `status_before_archive`. Member response
содержит `id`, `user_id`, `role`, `joined_at`, `first_name` и `last_name`.
Passport response содержит `id`, `project_id`, все перечисленные выше
business fields, `version`, `created_at` и `updated_at`. Стандартная
page-number envelope использует `count`, `next`, `previous`, `results`.

### Frontend

React Router и TanStack Query в существующей FSD-архитектуре:

- `/app` — список текущих проектов; `/app/projects/new` — форма создания;
  `/app/projects/archived` — архив; `/app/projects/:projectId` — обзор,
  участники и паспорт.
- `entities/project` владеет API типов и project/passport query keys;
  `features/project-*` — создание, metadata/passport editing и lifecycle
  actions; страницы композируют эти slices. API types генерируются из
  OpenAPI, вручную generated types не меняются.
- Страница проекта показывает статус и только разрешённые executor
  действия. Для customer нет edit controls; для completed/archived паспорт
  read-only. Backend остаётся источником разрешений.
- Запросы используют текущий same-origin client и session/CSRF. GET
  допускает явный retry; мутации не повторяются автоматически. Pending
  submit блокирует повторное нажатие. Успех обновляет соответствующие
  TanStack Query caches; ошибка оставляет локальный ввод. После stale
  version показывается конфликт и явное действие загрузить актуальную
  версию.
- UI придерживается существующего языка и визуальных конвенций приложения,
  семантических форм, keyboard navigation и responsive layout; нет
  completion percentage.

### Проверка

Основной шов — `projects` selectors/services, которые вызывают API и
тесты. Транзакционные service tests проверяют create и lifecycle; API
tests проверяют auth/verification, active membership, роли, project
isolation, статусы, ошибки и passport version. PostgreSQL migration
проверяется без очистки существующей БД/volumes. Frontend tests покрывают
формы, загрузку/ошибки и permission-aware controls. OpenAPI используется
для генерации TypeScript типов.

## Границы и швы

| Модуль | Владеет | Выставляет | Прячет |
|:--|:--|:--|:--|
| `projects` | Project, ProjectMember, ProjectPassport, project lifecycle и membership invariants | `create_project(*, actor, data) -> Project`; `complete_project(*, project_id, actor) -> Project`; `reopen_project(*, project_id, actor) -> Project`; `archive_project(*, project_id, actor) -> Project`; `restore_project(*, project_id, actor) -> Project`; selectors for member-scoped list/detail/members/passport; `update_passport(*, project_id, actor, expected_version, changes) -> ProjectPassport` | ORM mutation details, database constraints, transition validation, version compare-and-update; no Stage 03 invitation/member-acceptance workflow |
| `common` | ProjectAuditLog persistence and generic audit metadata writer | `record_project_action(*, project_id, actor_id, action, target_type, target_id, metadata) -> ProjectAuditLog` | audit model persistence details and safe metadata handling |
| Frontend project slices | Project queries, forms, lifecycle and passport interactions | typed query/mutation hooks consumed by pages | caching, request details and local mutation state |

**Тестовые швы:** `projects.services`/selectors for domain invariants,
`projects` REST API for auth/membership/role behavior, and React page/feature
boundaries for user states. Critical tests must use PostgreSQL for partial
unique constraints and transaction behavior; service/unit-level validation
may use the test runner's normal database.

## Вне рамок

| Требование | Почему не сейчас |
|:--|:--|
| R27 — customer invitation flow | Явно исключён из Stage 03 и принадлежит Stage 04. |
| R28 — questionnaire and passport auto-population | Явно исключено; mapping/requiredness остаются Stage 05 решениями. |
| R29 — Project State entities | Явно исключены; read-only политика завершённых проектов будет применена владельцем Project State. |
| R30 — progress percentages | Запрещены product invariant; не добавляем. |
| R31 — public freelance-order import | Явно исключён из MVP scope. |
| G10 — chat read-only после completion | Chat subsystem вне Stage 03; политика сохраняется для chat stage. |
| G11 — documents read/download без upload после completion | Documents subsystem вне Stage 03; политика сохраняется для document stage. |
| G12 — Project State read-only после completion | Project State subsystem вне Stage 03; политика сохраняется для его стадии. |
| G13 — не принимать questionnaire answers после completion | Questionnaire subsystem вне Stage 03; политика сохраняется для Stage 05. |
| G19 — расписание хранения и backup retention | 12 месяцев и 14 дней не утверждены; автоудаление/сроки хранения не реализуются и не обещаются. |
| G02 — draft → active после invitation acceptance | Точный триггер зафиксирован, но принятие invitation и применение status transition остаются за Stage 04. |

G17 — архив не удаляет проект или документы (История 9); здесь не
реализуется document deletion workflow. G20/G21 запрещают новые паспортные
поля и дополнительную обязательность (Истории 11 и 18). Только mapping
ответов анкеты и правила обязательности самих ответов остаются за Stage 05.

## Открытые места

Нет product placeholders. Технические defaults ниже явно приняты для
реализации и могут быть изменены только при сохранении утверждённых
полей и поведения:

| Решение | Assumption и родитель истории |
|:--|:--|
| Project name | `R09.1`: обязательная строка, trim по краям, максимум 200 символов; description nullable и optional. |
| Первичное состояние паспорта | `R07`/`R15.1`: non-null text fields начинаются как `""`; JSONB fields — `{}`; nullable date/decimal/currency — `null`. Это не вводит обязательность заполнения. |
| Project list | `R08.1`: page size 20, maximum 100, stable ordering `updated_at DESC, id ASC`; endpoint-local значения, потому что глобальный размер не утверждён. |
| Member summary | `R12.1`: active participants с ID, role, joined time, `first_name` и `last_name`; email не нужен для Stage 03 UI. |
| Currency | `R15.1`: ровно 3 ASCII letters, normalise to uppercase; список допустимых валют не фиксируется. |
| Completion timestamp | `R13.1`: `completed_at` показывает последнее завершение, поэтому reopen сохраняет его, новое завершение обновляет. |
| Audit granularity | `A01 → R17`: metadata содержит имена изменённых полей и transitions, но не введённые значения. |

## Покрытие манифеста

| Требование | Раздел спецификации |
|:--|:--|
| R01 | Истории 1; Решения по реализации — Модель и lifecycle |
| R02 | История 19; Read first и решения выше |
| R03 | История 19; Stage 02 dependency |
| R04 | История 1; Модель и lifecycle |
| R05 | История 2; API create |
| R06 | История 6; database constraints |
| R07 | История 1; create transaction |
| R08 | Истории 3, 4, 6–9; API table |
| R09 | Истории 1–2; API create |
| R10 | История 4; API detail |
| R11 | История 5; project PATCH |
| R12 | История 6; members endpoint |
| R13 | История 7; lifecycle service |
| R14 | История 9; archive/restore services |
| R15 | История 11; passport permissions |
| R16 | История 12; compare-and-update |
| R17 | Истории 4–6; active membership scope |
| R18 | История 3; Frontend |
| R19 | Истории 1–2; Frontend |
| R20 | История 4; Frontend |
| R21 | История 11; Frontend |
| R22 | История 11; passport permissions |
| R23 | Истории 3, 13; loading/empty/error states |
| R24 | История 3; empty state |
| R25 | Истории 5, 13; validation state |
| R26 | Истории 3, 13; error state |
| R27 | Вне рамок R27 |
| R28 | Вне рамок R28 |
| R29 | Вне рамок R29 |
| R30 | Вне рамок R30 |
| R31 | Вне рамок R31 |
| R32 | История 1; Модель и lifecycle |
| R33 | История 11; Границы и швы |
| R34 | Решения по реализации — API |
| R35 | Истории 3–5; Frontend |
| R36 | История 14; Проверка |
| R37 | История 1; verified authenticated permission |
| R38 | История 1; atomic creation |
| R39 | История 2; project type validation |
| R40 | История 4; member-scoped selector |
| R41 | История 5, 11; executor write permissions |
| R42 | История 11; passport read permissions |
| R43 | История 12; stale update behavior |
| R44 | История 6; conditional unique constraints |
| R45 | История 14; isolation/role tests |
| R46 | История 11; exact field list |
| R47 | Истории 11, 18; no added requiredness |
| R48 | История 19; scope |
| G01 | История 10; lifecycle enum |
| G02 | Вне рамок G02; Stage 04 transition boundary |
| G03 | История 7; complete action |
| G04 | История 8; reopen action |
| G05 | История 9; archive allowed sources |
| G06 | История 9; restore to prior status |
| G07 | История 9; `status_before_archive` |
| G08 | История 10; executor-only state changes |
| G09 | История 15; participant read access |
| G10 | История 16; Out of scope G10 |
| G11 | История 16; Out of scope G11 |
| G12 | История 16; Out of scope G12 |
| G13 | История 16; Out of scope G13 |
| G14 | История 9; archive list |
| G15 | История 17; archived member read access |
| G16 | История 9; archive write lock |
| G17 | История 9; archive preservation |
| G18 | История 9; no auto-delete |
| G19 | История 17; Out of scope G19 |
| G20 | История 18; exact field list |
| G21 | Истории 11, 18; no additional requiredness |
| G22 | История 10; default draft state |
| G23 | История 10; active state meaning |
| G24 | История 20; prerequisite |
| G25 | История 21; change discipline |
