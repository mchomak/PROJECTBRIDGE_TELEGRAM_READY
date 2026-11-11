# Манифест требований

Источник: `2026-11-11-brief.md`. Строку из этого списка может снять **только пользователь**.

| ID | Из брифа (дословно) | Статус | Основание | Где |
|---|---|---|---|---|
| R01 | «Create the custom Django user model before the first project migration.» | done | `DATA_MODEL.md` задаёт `AbstractUser`, UUID и `email_verified_at`. ASSUMPTION — принято за пользователя: email-only manager для `USERNAME_FIELD`; `first_name`/`last_name` optional и blank. Миграционный аудит нашёл только `common.0001_enable_pgvector`, а БД уже прошла стандартные `auth` миграции с `auth.User` и нулём пользователей. Создать `accounts.User` в `accounts.0001_initial`, не переписывая существующую историю; старую пустую таблицу `auth_user` оставить без изменений. | spec §2 → T01  commit 7265d78 |
| R02 | «Use normalized, unique email as the login identifier.» | done | ASSUMPTION — принято за пользователя: удалять пробелы по краям и приводить весь адрес к `casefold()` до проверки уникальности и сохранения. | spec §2 → T01  commit 7265d78 |
| R03 | «Use Django password hashing» | done | Использовать `set_password()` и штатный `check_password()`; plaintext не сохранять. ASSUMPTION — принято за пользователя: стандартные validators Django, минимум 8 символов плюс similarity/common/numeric checks. | spec §2 → T01  commit 7265d78 |
| R04 | «configure Argon2 as the preferred hasher if compatible with the selected environment.» | done | ASSUMPTION — принято за пользователя: добавить и проверить Argon2 на закреплённом Python 3.13; если пакет несовместим, оставить безопасный штатный Django hasher. | spec §2 → T01  commit 7265d78 |
| R05 | «Implement registration» | done | ASSUMPTION — принято за пользователя: регистрация принимает email и password, создаёт неподтверждённый аккаунт и отправляет письмо; сессию создаёт отдельный login endpoint. | spec §3 → T02  commit 96e6c61 |
| R06 | «login» | done | ASSUMPTION — принято за пользователя: явный login создаёт сессию; login разрешён до подтверждения, но frontend закрывает product routes для unverified email. | spec §3, §7 → T02  commit 96e6c61 |
| R07 | «logout» | done | ASSUMPTION — принято за пользователя: успешный logout завершает Django session и возвращает 204. | spec §3 → T02  commit 96e6c61 |
| R08 | «current-user» | done | ASSUMPTION — принято за пользователя: профиль возвращает UUID, email, first/last name и вычисленные verified bool/timestamp. | spec §3 → T02  commit 96e6c61 |
| R09 | «email-verification resend» | done | ASSUMPTION — принято за пользователя: публичный resend принимает email; для уже вошедшего пользователя использует его email. Ответ не раскрывает наличие аккаунта. | spec §3 → T03  commit 11d4c1c |
| R10 | «verification confirmation.» | done | ASSUMPTION — принято за пользователя: успешное подтверждение не создаёт сессию, пользователь входит отдельно. | spec §3, §4 → T03  commit 11d4c1c |
| R11 | «Generate high-entropy verification tokens» | done | ASSUMPTION — принято за пользователя: криптографический токен на 256 бит (`token_urlsafe(32)`), с одноразовым использованием. | spec §4 → T01, T03  commit 11d4c1c |
| R12 | «store only token hashes» | done | ASSUMPTION — принято за пользователя: хранить SHA-256 хеш; сырой токен только в доставляемой ссылке. | spec §4 → T01, T03  commit 11d4c1c |
| R13 | «enforce expiration» | done | ASSUMPTION — принято за пользователя: токен действует 24 часа. | spec §4 → T01, T03  commit 11d4c1c |
| R14 | «single use.» | done | ASSUMPTION — принято за пользователя: при повторной отправке помечать прежние активные токены использованными; подтверждённый токен больше не принимать. | spec §4 → T01, T03  commit 11d4c1c |
| R15 | «Use session authentication» | done | — | spec §5 → T02  commit 96e6c61 |
| R16 | «with HttpOnly cookies» | done | Сессионная cookie HttpOnly; CSRF cookie доступна клиенту только для заголовка CSRF. ASSUMPTION — принято за пользователя: обе используют `SameSite=Lax`. | spec §5 → T02  commit 96e6c61 |
| R17 | «and CSRF protection.» | done | CSRF действует для всех unsafe browser methods (POST, PUT, PATCH, DELETE), анонимных и аутентифицированных; login/register/resend/confirm проверяются явно. | spec §5 → T02  commit 96e6c61 |
| R18 | «Configure local console email delivery.» | done | — | spec §4 → T03  commit 11d4c1c |
| R19 | «Add rate limiting or a clearly documented initial protection for registration and verification endpoints.» | done | ASSUMPTION — принято за пользователя: включить общие DRF scoped throttles на Redis cache; начальные лимиты: register 5/hour, login 10/minute, resend 3/hour, confirm 10/hour; числа документировать как стартовую защиту. | spec §6 → T03  commit 11d4c1c |
| R20 | «Add common authentication and unauthenticated response handling.» | done | API ошибки должны использовать общий envelope; анонимный доступ к защищённым ресурсам возвращает 401, недостаток прав — 403. | spec §3, §5 → T02  commit 96e6c61 |
| R21 | «Build registration» | done | ASSUMPTION — принято за пользователя: страницы имеют маршруты `/register` и `/login`; формы показывают validation и network states. | spec §7 → T04; commit 7c0cb4c |
| R22 | «login» | done | — | spec §7 → T05; commit 6a1f85e |
| R23 | «email-verification» | done | ASSUMPTION — принято за пользователя: токен передавать в URL fragment, чтобы он не попадал в HTTP запрос к frontend серверу. | spec §7 → T04; commit 7c0cb4c |
| R24 | «authenticated-session states using FSD.» | done | ASSUMPTION — принято за пользователя: непроверенный пользователь может войти для завершения проверки, но защищённые продуктовые маршруты доступны только подтверждённому email. FSD страницы: `/login`, `/register`, `/verify-email`, `/verification-required`, `/app`. | spec §7 → T04; commit 7c0cb4c |
| R25 | «Load the current user from the backend.» | done | — | spec §7 → T04; commit 7c0cb4c |
| R26 | «Handle expired sessions» | done | ASSUMPTION — принято за пользователя: сбросить кэш пользователя и перейти на login при 401; временную сеть/ошибку сервера показывать отдельно. | spec §7 → T04; commit 7c0cb4c |
| R27 | «unauthenticated navigation.» | done | — | spec §7 → T04; commit 7c0cb4c |
| R28 | «Do not store session credentials in local storage.» | done | Использовать только same-origin session cookie; пароль и токен email не сохранять в persistent browser storage. | spec §5, §7 → T04; commit 7c0cb4c |
| R29 | «Social login or SSO.» | deferred | Out of scope Stage 02. | — |
| R30 | «Multi-factor authentication.» | deferred | Out of scope Stage 02. | — |
| R31 | «Password reset unless the product owner resolves the corresponding open decision.» | deferred | `OPEN_DECISIONS.md` §25 остаётся открытым; Stage 02 прямо исключает password reset. | — |
| R32 | «Account deletion/deactivation workflows.» | deferred | Out of scope Stage 02; решение остаётся в `OPEN_DECISIONS.md` §9. | — |
| R33 | «Project-specific roles; those arrive in Stage 03.» | deferred | Out of scope Stage 02. | — |
| R34 | «Custom user model and migrations.» | done | Создать новую модель аккаунтов в отдельной миграции; не изменять `common.0001_enable_pgvector`. | spec §2 → T01  commit 7265d78 |
| R35 | «Authentication REST endpoints.» | done | Сохранить перечисленные endpoint paths из `API_CONTRACT.md` §5. | spec §3 → T02, T03  commit 11d4c1c |
| R36 | «Email verification flow.» | done | — | spec §4 → T03  commit 11d4c1c |
| R37 | «Session/CSRF configuration.» | done | В production установить secure session и CSRF cookie. | spec §5 → T02  commit 96e6c61 |
| R38 | «Frontend auth screens and route guards.» | done | — | spec §7 → T04; commit 7c0cb4c |
| R39 | «Tests for authentication and verification.» | done | ASSUMPTION — принято за пользователя: backend tests использовать текущие pytest/Django APIClient seams; frontend tests — текущие Vitest/testing-library seams. Проверить успех, ошибки и границы доступа. | spec §8 → T03, T04; commit 7c0cb4c |
| R40 | «A user can register with a valid email and password.» | done | — | spec §3, §8 → T02  commit 96e6c61 |
| R41 | «Duplicate normalized emails are rejected.» | done | На уровне сервиса и DB unique constraint. | spec §2, §8 → T01, T02  commit 96e6c61 |
| R42 | «Passwords are stored only as secure hashes.» | done | — | spec §2, §8 → T01, T02  commit 96e6c61 |
| R43 | «A user can log in, retrieve their current profile, and log out.» | done | — | spec §3, §8 → T02, T04; commit 7c0cb4c |
| R44 | «Email verification tokens expire and cannot be reused.» | done | — | spec §4, §8 → T01, T03  commit 11d4c1c |
| R45 | «Unverified accounts cannot be treated as email-verified.» | done | Не позволять Stage 02 flow выставлять verified без валидного токена; профиль явно возвращает false/null. | spec §4, §8 → T03  commit 11d4c1c |
| R46 | «CSRF protection applies to state-changing browser requests.» | done | — | spec §5, §8 → T02, T03  commit 11d4c1c |
| R47 | «Session cookies are HttpOnly» | done | — | spec §5, §8 → T02  commit 96e6c61 |
| R48 | «production cookie settings are secure by default.» | done | — | spec §5, §8 → T02  commit 96e6c61 |
| R49 | «Frontend does not store session tokens in local storage.» | done | — | spec §7, §8 → T04; commit 7c0cb4c |
| R50 | «Tests cover invalid credentials» | done | — | spec §8 → T02  commit 96e6c61 |
| R51 | «duplicate emails» | done | — | spec §8 → T02  commit 96e6c61 |
| R52 | «expired/reused tokens» | done | — | spec §8 → T03  commit 11d4c1c |
| R53 | «CSRF/session behavior.» | done | — | spec §8 → T02, T03, T04; commit 7c0cb4c |
| R54 | «If the existing repository already has a user model or migrations, inspect them before changing `AUTH_USER_MODEL`.» | done | Выполнено: accounts app пустая; единственная проектная миграция включает pgvector; в БД применены стандартные auth миграции, текущий `auth.User` содержит 0 записей. | spec §2 → T01  commit 7265d78 |
| R55 | «Do not replace an established user model or rewrite migrations without a migration plan.» | done | ASSUMPTION — принято за пользователя: аддитивно добавить `accounts.User`, не менять старые миграции и не переносить отсутствующих пользователей. Проверить план и clean DB до применения к локальному runtime. | spec §2, §8 → T01  commit 7265d78 |
| R56 | «Implement Stage 02 only.» | done | Не добавлять роли, приглашения, reset, удаление аккаунта или другие будущие функции. | spec §1 → T01  commit 7265d78 |
| R57 | «Read the account, API, and security contracts first.» | done | Прочитаны все перечисленные документы и brief Stage 02. | spec §1 → T01  commit 7265d78 |
| R58 | «Do not add password reset or unrelated account features.» | deferred | Password reset остаётся открытым в `OPEN_DECISIONS.md`; прочие аккаунтные workflow вне Stage 02. | — |
| R59 | «забей на панель, просто выполни все задачи» | done | Выполнять Stage 02 без действий с Autopilot dashboard. | spec §1 → T01, T02, T03, T04; commit 7c0cb4c |

## Самобрифинг — принятые решения

- ASSUMPTION — принято за пользователя: `first_name` и `last_name` остаются пустыми и необязательными; форма регистрации собирает только email и password.
- ASSUMPTION — принято за пользователя: стандартная Django password validation с минимальной длиной 8 символов; Argon2 является первым hasher, если закреплённый runtime его поддерживает.
- ASSUMPTION — принято за пользователя: парольный вход разрешён неподтверждённому аккаунту только ради перехода к проверке; frontend не открывает подтверждённому email никаких Stage 03 product routes.
- ASSUMPTION — принято за пользователя: успешная регистрация не создаёт сессию; пользователь подтверждает адрес, затем выполняет явный login.
- ASSUMPTION — принято за пользователя: локальная ссылка подтверждения использует `FRONTEND_BASE_URL` (по умолчанию `http://localhost:5173`) и URL fragment; production задаёт собственный frontend origin.
- ASSUMPTION — принято за пользователя: регистрация возвращает понятную ошибку при дубликате; login, resend и invalid/expired/reused verification не раскрывают лишние сведения об аккаунте.
- ASSUMPTION — принято за пользователя: консольный email backend — локальная доставка проверочного сообщения; код приложения не пишет raw token в собственные логи или API ответы.
