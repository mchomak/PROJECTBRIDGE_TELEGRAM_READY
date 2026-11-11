# 01 — Модель аккаунта и migration plan

**Требования:** R01, R02, R03, R04, R11, R12, R13, R14, R34, R41, R42, R44, R54, R55, R56, R57, R59
**Blocked by:** —
**Зона:** `backend/apps/accounts/`, `backend/apps/common/api/`, `backend/config/settings/`, `backend/config/tests/test_production_settings.py`, `backend/config/urls.py`, `backend/requirements.txt`, `.env.example`, `docker-compose.yml`, `docs/database/`, `docs/adr/`
**Волна:** 1
**Status:** done

## Что должно заработать

В ProjectBridge появляется единая email-модель аккаунта и безопасный доменный слой для email verification. Существующие миграции сохраняются; текущая пустая `auth_user` не удаляется. Эта основа позволяет параллельно подключить REST-вход и endpoints подтверждения.

## Из брифа, дословно

> «Create the custom Django user model before the first project migration.»
> «Use normalized, unique email as the login identifier.»
> «Use Django password hashing; configure Argon2 as the preferred hasher if compatible with the selected environment.»
> «Generate high-entropy verification tokens, store only token hashes, enforce expiration and single use.»
> «If the existing repository already has a user model or migrations, inspect them before changing `AUTH_USER_MODEL`.»
> «Do not replace an established user model or rewrite migrations without a migration plan.»

## Разделы спецификации

Истории 1–3 и 9; Решения §1–7; Границы §1–3.

## Критерии приёмки

- [ ] `AUTH_USER_MODEL` указывает на `accounts.User` (Django app label `accounts`, Python package `apps.accounts`); email-only manager нормализует email, UUID — primary key, `email_verified_at` null до подтверждения; имена необязательные и blank.
- [ ] `accounts.0001_initial` создаёт User и EmailVerificationToken. Существующие миграции не меняются, legacy `auth_user` остаётся; `makemigrations --check` чистый.
- [ ] Миграции проходят на отдельной пустой PostgreSQL базе и на текущей локальной базе без удаления данных или volumes.
- [ ] `set_password()`/Django validators работают; Argon2 первым hasher только после установки и проверки в pinned Python 3.13, PBKDF2 остаётся для чтения совместимых hash.
- [ ] Проверочный токен генерируется с 256-bit entropy; в БД хранится только digest; expiry 24 часа; resend ротирует предыдущий active token; confirm сервиса проверяет expiry/use и atomically consumes token.
- [ ] Сервисные тесты покрывают email normalization, password hash, duplicate constraint, raw token отсутствует в модели/логах, истечение и повторное использование.
- [ ] Runtime получает Redis-backed cache и initial throttle scopes, local frontend URL, production Secure cookie defaults, общий DRF error envelope и JSON CSRF failure response; Stage 02 URL router включает отдельные core/verification URL modules.
- [ ] Обновлены DATA_MODEL migration/normalization details и ADR с обоснованием additive migration strategy; account lifecycle и password reset остаются открытыми/вне scope.

## Ограничения

Не переносить users, не удалять стандартные Django auth tables и не менять `common.0001_enable_pgvector`. Если clean/current database migration plan требует rewrite или destructive reset, вернуть `BLOCKED` с точными фактами.