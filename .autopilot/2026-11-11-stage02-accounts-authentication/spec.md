# Спецификация: Stage 02 — Accounts and Authentication

## Исходные документы

До спецификации прочитаны:

- `AGENTS.md` и `docs/README.md`;
- `docs/product/MVP_SCOPE.md`;
- `docs/database/DATA_MODEL.md`;
- `docs/api/API_CONTRACT.md`;
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`;
- `docs/architecture/BACKEND_ARCHITECTURE.md` и `docs/architecture/FRONTEND_ARCHITECTURE.md`;
- `docs/OPEN_DECISIONS.md`;
- `docs/implementation/stages/02-accounts-and-authentication.md`.

## Задача

Пользователю ProjectBridge нужен безопасный аккаунт на email, подтверждение владения адресом и привычный вход в браузере. Сейчас приложение — каркас без аккаунтов, поэтому пользователь не может войти и продолжить работу между посещениями.

## Решение

Добавить email-аккаунты и проверочный email-поток, сессию браузера и экраны регистрации, входа и подтверждения адреса. Пользователь сможет получить свой профиль и выйти. Неподтверждённый email будет явно показан как неподтверждённый; Stage 02 не откроет такому аккаунту защищённые продуктовые маршруты.

Stage 02 выполняется без открытия или обслуживания Autopilot dashboard по дополнению пользователя.

## Пользовательские истории

| # | Метка | История | Приёмка |
|---|---|---|---|
| 1 | R01, R34, R54, R55 | Как пользователь, я создаю аккаунт в новой модели, чтобы дальнейшие этапы ссылались на устойчивый идентификатор. | В чистой БД создаётся `accounts.User` с UUID; существующая история миграций не переписывается. Текущая БД проверена: `auth.User` не содержит записей; новая миграция добавляет custom user, не удаляя пустую таблицу `auth_user`. |
| 2 | R02, R41 | Как пользователь, я регистрирую email в одном нормализованном виде, чтобы одинаковый адрес нельзя было зарегистрировать повторно из-за регистра или пробелов. | До проверки уникальности email обрезается и приводится к `casefold()`; уникальное ограничение БД и проверка сервиса отклоняют дубликат. |
| 3 | R03, R04, R42 | Как пользователь, я задаю пароль, чтобы приложение хранило только проверяемый безопасный хеш. | `set_password()` создаёт хеш; plaintext не сохраняется. ASSUMPTION — Argon2 настроен первым hasher после успешной установки на Python 3.13; Django PBKDF2 остаётся для совместимости. |
| 4 | R05, R40 | Как посетитель, я регистрируюсь по email и паролю, чтобы получить неподтверждённый аккаунт. | Валидные данные создают аккаунт с `email_verified_at = null`, токен и письмо. Невалидный email, слишком короткий/слабый пароль и дубль возвращают понятные поля ошибок; регистрация не создаёт сессию. |
| 5 | R06, R43, R50 | Как пользователь, я вхожу по email и паролю, чтобы получить браузерную сессию. | Верные данные устанавливают Django session cookie; неверные данные дают одинаковую 401 ошибку без уточнения, какой реквизит не подошёл. Неподтверждённый пользователь может войти только в поток проверки адреса. |
| 6 | R07, R43 | Как вошедший пользователь, я выхожу, чтобы завершить текущую сессию. | Logout очищает сессию и возвращает 204; последующий запрос профиля получает 401. |
| 7 | R08, R25, R43, R45 | Как вошедший пользователь, я загружаю профиль с сервера, чтобы интерфейс показывал фактическое состояние аккаунта. | Профиль содержит id, нормализованный email, пустые/заполненные имя и фамилию, `email_verified` и `email_verified_at`; неподтверждённый аккаунт возвращается явно как false/null. |
| 8 | R09 | Как пользователь, я запрашиваю новое письмо подтверждения, чтобы восстановить доступ к проверке адреса. | Публичный запрос использует введённый email; аутентифицированный запрос может использовать только собственный email. Для неизвестного, уже подтверждённого или подходящего аккаунта возвращается одинаковый нейтральный результат. |
| 9 | R10, R11, R12, R13, R14, R36, R44 | Как пользователь, я подтверждаю email ссылкой, чтобы адрес был признан проверенным. | Токен создаётся криптографически случайным с энтропией 256 бит; в БД лежит только SHA-256 hash. Токен живёт 24 часа, применяется один раз; повторная отправка завершает прежние токены. Подтверждение устанавливает timestamp. Неверный, просроченный и использованный токены получают один общий ответ без различения причины. |
| 10 | R18 | Как локальный разработчик, я проверяю email-поток без внешнего провайдера, чтобы тестировать Stage 02 на своей машине. | Django console email backend печатает письмо в локальный backend console; API и приложение не возвращают и не журналируют raw token. |
| 11 | R15, R16, R17, R37, R46, R47, R48 | Как пользователь браузера, я остаюсь вошедшим через HttpOnly session cookie, а изменяющие запросы защищены от CSRF. | Session authentication использует Django cookies; `SESSION_COOKIE_HTTPONLY=True`; в production session и CSRF cookies имеют `Secure=True`. ASSUMPTION — обе cookie используют `SameSite=Lax`. CSRF bootstrap устанавливает cookie и возвращает token. Все unsafe browser methods (POST, PUT, PATCH, DELETE) требуют валидный CSRF token. Анонимные Stage 02 write endpoints (register/login/resend/confirm) явно проходят CSRF; защищённые DRF endpoints проверяются session authentication. |
| 12 | R19 | Как оператор приложения, я уменьшаю автоматические попытки регистрации и перебора/повторной отправки токенов, чтобы снизить базовый риск злоупотребления. | DRF scoped throttles используют общий Redis cache в runtime. Начальные лимиты: register 5/hour, login 10/minute, resend 3/hour, confirm 10/hour; превышение даёт 429. Лимиты обозначены стартовыми, не финальными значениями для всех API. |
| 13 | R20 | Как клиент API, я получаю одинаковый понятный формат ошибки, чтобы обработать истёкшую сессию и отказ доступа без разбора HTML или Django internals. | Ошибка содержит `code`, `detail`, `errors` и UUID `request_id`; unauthenticated защищённый REST request возвращает 401, аутентифицированный запрет — 403; CSRF failure возвращает JSON error envelope. Stack traces и secrets не раскрываются. |
| 14 | R21, R22, R23, R24, R38 | Как посетитель, я регистрируюсь, вхожу и подтверждаю email через доступные страницы, чтобы закончить настройку аккаунта. | ASSUMPTION — FSD-структура использует маршруты `/login`, `/register`, `/verify-email`, `/verification-required` и `/app`, разделяет user entity, auth actions и страницы. Формы доступны с клавиатуры и экранного чтения, сохраняют ввод при серверной validation error и показывают pending/success/failure состояния. |
| 15 | R26, R27 | Как пользователь, я перенаправляюсь на login после истечения сессии, чтобы защищённая страница не показывала старое состояние. | `GET /me` 401 очищает user query и перенаправляет защищённый маршрут на login; временная сеть/серверная ошибка показывает retry state, а не выдаёт её за logout. |
| 16 | R28, R49 | Как пользователь, я не оставляю session credential в постоянном хранилище браузера, чтобы приложение не сохраняло bearer token на клиенте. | Пароль и токены остаются только в форме/операции памяти; frontend не читает и не пишет `localStorage` для session credentials. Session cookie автоматически передаётся same-origin. |
| 17 | R39, R50, R51, R52, R53 | Как сопровождающий, я прогоняю тесты успеха и защиты, чтобы ключевые ветви аккаунта проверялись при изменениях. | Backend tests проверяют регистрацию, дубликат, пароль hash, login/logout/me, неверные данные, CSRF для анонимных и аутентифицированных запросов, HttpOnly/Secure cookie settings, email, throttle и missing/expired/reused token. Frontend tests проверяют формы, route guards, 401/network state и отсутствие persistent auth storage. |
| 18 | R56, R57, R58, R59 | Как владелец продукта, я получаю только Stage 02 и ожидаю, что заданные контракты будут прочитаны до реализации. | Реализация не добавляет password reset, MFA, SSO, account deletion/deactivation, project roles или workflow следующих стадий. Исходные account/API/security документы сверены; Autopilot dashboard не используется согласно дополнению. |

## Решения по реализации

1. **Модель аккаунта.** `accounts.User` наследуется от `AbstractUser`, использует UUID, unique email как `USERNAME_FIELD`, собственный manager и nullable `email_verified_at`; `first_name` и `last_name` остаются необязательными и пустыми по умолчанию. Регистрация запрашивает только email и password. Это следует модели Accounts и форме из acceptance criteria.
2. **Email normalization.** Нормализовать через trim + Unicode `casefold()` всю строку до сохранения/сравнения. Так регистрация и будущие email-bound invitations смогут применять один детерминированный ключ. Это ASSUMPTION; редкий регистрочувствительный local-part не поддерживается.
3. **Миграционный план.** Stage 01 уже применил миграции `auth.User` и `common.0001_enable_pgvector`, но в текущей БД `auth.User` пуст. Не менять ни одну существующую миграцию. Настроить `AUTH_USER_MODEL = "accounts.User"` и добавить `accounts.0001_initial`, зависящую от требуемой миграции `auth`; оставить старую пустую таблицу `auth_user` как legacy. Проверить миграционный граф на отдельной пустой БД и применить новые миграции к локальной БД без удаления данных/volume. Новые связи следующих этапов должны ссылаться через `settings.AUTH_USER_MODEL`.
4. **Пароль.** ASSUMPTION — применять стандартные Django password validators с минимальной длиной 8 и similarity/common/numeric checks. Argon2 включить первым в `PASSWORD_HASHERS` только после проверки установки `argon2-cffi` в pinned Python 3.13; PBKDF2 оставить после него для проверки существующих Django hashes.
5. **Состояние email.** `email_verified_at is None` означает неподтверждённый адрес; API вычисляет `email_verified` из timestamp, а не хранит два источника истины. Явный login допустим до подтверждения, чтобы продолжить account verification; frontend закрывает непроверенному пользователю Stage 03 product routes. Signup не создаёт сессию; после подтверждения пользователь входит обычным login.
6. **Схема проверки.** `EmailVerificationToken` содержит UUID, FK на User, unique 64-char `token_hash`, `expires_at`, nullable `used_at`, `created_at`. ASSUMPTION — токен `secrets.token_urlsafe(32)` (256 бит); в базе хранится SHA-256 digest. ASSUMPTION — один активный токен на пользователя: resend помечает прежний использованным в транзакции, затем создаёт новый с TTL 24 часа. Confirm выполняет lookup digest и consume атомарно, используя row lock, проверяет срок/used state и устанавливает `email_verified_at` один раз.
7. **Письма.** Использовать Django email backend. Локальная настройка — console backend; ссылка строится из `FRONTEND_BASE_URL` (локальный default `http://localhost:5173`) и ведёт на `/verify-email#token=...`. Fragment не уходит в HTTP request к frontend server. Production deploy задаёт собственный URL; email provider остаётся вне этого stage.
8. **API.** Следовать семи endpoint paths из `API_CONTRACT.md` §5. ASSUMPTION — `register` принимает `{email,password}`, возвращает 201 user summary и отправляет письмо, но не login. `login` принимает те же credentials и возвращает 200 user summary вместе с session cookie. `logout` — 204. `me` возвращает профиль. `resend` принимает email публично или использует текущий пользовательский email; ответ не раскрывает наличие аккаунта. `confirm` принимает token в JSON body и возвращает verified state; неверные/просроченные/использованные токены не различаются. `csrf` возвращает CSRF context и устанавливает cookie.
9. **CSRF и cookies.** Django session middleware и CSRF middleware остаются центральными. DRF `SessionAuthentication` применяется к API; login/register/resend/confirm отдельно проходят CSRF, потому что анонимные `SessionAuthentication` запросы сами по себе CSRF не проверяет. CSRF cookie должна читаться общим same-origin API client, session cookie остаётся HttpOnly. В production обе cookie secure; локально без HTTPS cookies не Secure.
10. **Лимиты.** Scoped DRF throttling работает через Django Redis cache. ASSUMPTION — начальные auth scopes: register 5/hour, login 10/minute, resend 3/hour, confirm 10/hour. `OPEN_DECISIONS.md` item 21 остаётся открытым для прочих endpoint groups и финального пересмотра чисел.
11. **Общие ошибки.** DRF exception handler нормализует ошибки в `{code, detail, errors, request_id}`; отдельный CSRF failure view делает то же для middleware отказа. Неподтверждённая сессия получает 401, permission denial — 403. Login и verification ошибки не дают деталей для enumeration.
12. **Frontend.** `entities/user` описывает профиль и current-user query; `features/auth` владеет register/login/logout/resend/confirm; pages собирают `/login`, `/register`, `/verify-email`, `/verification-required` и защищённый `/app`. ASSUMPTION — Router остаётся BrowserRouter; raw verification token передаётся в fragment, читается один раз и сразу удаляется из address bar. TanStack Query держит только user profile in-memory. Shared API boundary добавляет same-origin credentials и автоматически получает CSRF context перед write, если cookie ещё нет.
13. **Типы.** OpenAPI генерируется из views/serializers через drf-spectacular, затем фронтенд types генерируются штатной командой. Generated declarations не редактировать вручную.
14. **Неизвестные поля.** First/last name пустые и необязательные; роль пользователя в проекте не существует до Stage 03. Изменять проектную модель, инвайты и приглашённые email в этом этапе не нужно.

## Границы и швы

| Модуль | Владеет | Выставляет | Прячет |
|---|---|---|---|
| `accounts` backend | User, email verification tokens, normalization, auth state transitions, mail creation | `register_user(email, password) -> User`; `authenticate_user(email, password) -> User \| None`; `resend_verification(email) -> None`; `confirm_verification(raw_token) -> User` | Django model persistence, token digest lookup/rotation, transaction locks, email body creation |
| `accounts.api` | REST serializers, permissions, views and OpenAPI schemas | seven REST endpoints from `API_CONTRACT.md` §5 | request parsing and mapping to service errors |
| `common` API support | stable API error envelope and CSRF failure response | DRF exception handler and `csrf_failure(request, reason) -> HttpResponse` | error code mapping and request ID creation |
| `entities/user` frontend | authenticated profile shape and current-user query | `useCurrentUser()` / `User` profile type from generated OpenAPI types | query cache details |
| `features/auth` frontend | auth actions and CSRF-aware requests | `register`, `login`, `logout`, `resendVerification`, `confirmVerification` mutations | endpoint payload wiring and mutation state |
| `pages/auth` frontend | auth route composition and guards | login/register/verify/verification-required/app routes | forms and presentation details from lower layers |
| `shared/api` frontend | same-origin request and CSRF boundary | `apiRequest(path, init)` and generated API types | cookie parsing and CSRF bootstrap sequence |

**Test seams:** backend behavior is checked through REST/APIClient plus the accounts service public signatures for race-sensitive token behavior; frontend behavior is checked through page rendering and shared API boundary. Use Django email outbox and database transactions as test tools, not alternate production interfaces.

## Вне рамок

| Требование | Почему не сейчас |
|---|---|
| R29 | Social login/SSO is explicitly out of Stage 02. |
| R30 | MFA is explicitly out of Stage 02. |
| R31, R58 | Password reset remains open in `OPEN_DECISIONS.md` item 25 and Stage 02 explicitly forbids adding it without resolution. |
| R32 | Account deletion/deactivation remains open in `OPEN_DECISIONS.md` item 9 and is outside this stage. |
| R33 | Project-specific roles belong to Stage 03. |

## Открытые места

Нет placeholders, блокирующих Stage 02. Password reset, account lifecycle, production email provider, and final limits for other API endpoint groups remain documented product decisions and are outside this stage.

## Покрытие манифеста

| Требование | Раздел спецификации |
|---|---|
| R01 | Истории 1; Решения 1, 3 |
| R02 | Истории 2; Решения 2 |
| R03 | Истории 3; Решения 4 |
| R04 | Истории 3; Решения 4 |
| R05 | Истории 4; Решения 8 |
| R06 | Истории 5; Решения 8 |
| R07 | Истории 6; Решения 8 |
| R08 | Истории 7; Решения 8 |
| R09 | Истории 8; Решения 8 |
| R10 | Истории 9; Решения 6, 8 |
| R11 | Истории 9; Решения 6 |
| R12 | Истории 9; Решения 6 |
| R13 | Истории 9; Решения 6 |
| R14 | Истории 9; Решения 6 |
| R15 | Истории 11; Решения 9 |
| R16 | Истории 11; Решения 9 |
| R17 | Истории 11; Решения 9 |
| R18 | Истории 10; Решения 7 |
| R19 | Истории 12; Решения 10 |
| R20 | Истории 13; Решения 11 |
| R21 | Истории 14; Решения 12 |
| R22 | Истории 14; Решения 12 |
| R23 | Истории 14; Решения 7, 12 |
| R24 | Истории 14; Решения 12 |
| R25 | Истории 7; Решения 12 |
| R26 | Истории 15; Решения 12 |
| R27 | Истории 15; Решения 12 |
| R28 | Истории 16; Решения 12 |
| R29 | Вне рамок |
| R30 | Вне рамок |
| R31 | Вне рамок |
| R32 | Вне рамок |
| R33 | Вне рамок |
| R34 | Истории 1; Решения 1, 3 |
| R35 | Решения 8 |
| R36 | Истории 9; Решения 6 |
| R37 | Истории 11; Решения 9 |
| R38 | Истории 14; Решения 12 |
| R39 | Истории 17 |
| R40 | Истории 4 |
| R41 | Истории 2; Решения 2 |
| R42 | Истории 3 |
| R43 | Истории 5, 6, 7 |
| R44 | Истории 9 |
| R45 | Истории 7, 9 |
| R46 | Истории 11 |
| R47 | Истории 11 |
| R48 | Истории 11 |
| R49 | Истории 16 |
| R50 | Истории 5, 17 |
| R51 | Истории 17 |
| R52 | Истории 17 |
| R53 | Истории 17 |
| R54 | Истории 1; Решения 3 |
| R55 | Истории 1; Решения 3 |
| R56 | Истории 18; Решения 14 |
| R57 | Истории 18 |
| R58 | Вне рамок |
| R59 | Задача; Истории 18 |