# 02 — Session auth API

**Требования:** R05, R06, R07, R08, R15, R16, R17, R20, R35, R37, R40, R41, R42, R43, R46, R47, R48, R50, R51, R53, R59
**Blocked by:** 01
**Зона:** `backend/apps/accounts/api/core/`, `backend/apps/accounts/api/core_urls.py`, `backend/apps/accounts/tests/api/test_auth.py`, `docs/api/`, `docs/security/`, `docs/OPEN_DECISIONS.md`
**Волна:** 2
**Status:** done

## Что должно заработать

Посетитель может создать неподтверждённый аккаунт, затем войти, запросить профиль и завершить сессию. Каждый API ответ соответствует контракту ProjectBridge, включая единый формат отказов и CSRF на browser writes.

## Из брифа, дословно

> «Implement registration, login, logout, current-user»
> «Use session authentication with HttpOnly cookies and CSRF protection.»
> «Add common authentication and unauthenticated response handling.»
> «A user can register with a valid email and password.»
> «A user can log in, retrieve their current profile, and log out.»

## Разделы спецификации

Истории 4–8, 11 и 13; Решения §5, §8–11; Границы §1–3.

## Критерии приёмки

- [ ] Реализованы `GET /api/v1/auth/csrf/`, `POST /register/`, `POST /login/`, `POST /logout/`, `GET /me/` с OpenAPI schemas по API contract.
- [ ] Регистрация использует `register_user`, возвращает 201 user summary без сессии; normalized duplicate возвращает понятную 400 field error.
- [ ] Login устанавливает HttpOnly Django session cookie; неверная пара возвращает общий 401 без указания неверного поля; unverified email остаётся false.
- [ ] `me` возвращает профиль только текущей сессии; unauthenticated запрос — 401. Logout очищает сессию и возвращает 204.
- [ ] CSRF bootstrap устанавливает контекст; анонимные register/login запросы без CSRF отклоняются и проходят с корректным token. Middleware/DRF ошибки используют JSON envelope с `code`, `detail`, `errors`, `request_id`.
- [ ] Тесты покрывают valid registration, duplicate normalized email, password hash, invalid credentials, login/me/logout session, HttpOnly cookie и CSRF.
- [ ] API_CONTRACT.md и ACCESS_CONTROL_AND_SECURITY.md описывают session/API errors и initial auth rate protection; OPEN_DECISIONS.md обновлён только по Stage 02 auth-rate decision, password reset остаётся open.

## Ограничения

Не создавать project roles, membership, invitations, password reset или account deletion endpoints.