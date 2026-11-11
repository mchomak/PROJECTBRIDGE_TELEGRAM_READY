# 04 — Frontend auth flows and route guards

**Требования:** R21, R22, R23, R24, R25, R26, R27, R28, R38, R39, R43, R49, R53, R59
**Blocked by:** 02, 03
**Зона:** `frontend/src/`, `frontend/package.json`, `frontend/package-lock.json`, `docs/architecture/FRONTEND_ARCHITECTURE.md`
**Волна:** 3
**Status:** review

## Что должно заработать

Пользователь может зарегистрироваться, войти, проверить адрес, видеть свой текущий session state и выйти. При старой/истёкшей сессии защищённые маршруты ведут на login; network failures остаются видимыми и повторяемыми.

## Из брифа, дословно

> «Build registration, login, email-verification, and authenticated-session states using FSD.»
> «Load the current user from the backend.»
> «Handle expired sessions and unauthenticated navigation.»
> «Do not store session credentials in local storage.»
> «Frontend does not store session tokens in local storage.»

## Разделы спецификации

Истории 5–8, 14–17; Решения §7, §12–13; Границы §4–7.

## Критерии приёмки

- [ ] FSD-страницы login, register, verify-email, verification-required и защищённое app состояние работают через существующий BrowserRouter.
- [ ] Current user загружается с `/me`; вход/выход/регистрация/повторная отправка/подтверждение используют API; verified guard не открывает unverified product routes.
- [ ] Shared API client перед unsafe request автоматически получает CSRF context, добавляет CSRF header и отправляет same-origin credentials.
- [ ] Token читается один раз из URL fragment и удаляется из address bar; auth/session credentials не записываются в localStorage.
- [ ] 401 очищает in-memory user state и переводит на login; network/5xx показывают понятное retry состояние, а validation errors сохраняют введённые поля, кроме password.
- [ ] OpenAPI types сгенерированы штатной командой из работающего backend; generated файл не правился вручную.
- [ ] Vitest/testing-library покрывает формы, route guards, verified/unverified state, session expiry/network errors и отсутствие localStorage writes; frontend format/lint/typecheck/test/build проходят.
- [ ] FRONTEND_ARCHITECTURE.md описывает cookies/CSRF и guard, не добавляя будущие продуктовые маршруты.

## Ограничения

Не добавлять проектные экраны, роли, dashboard или токены сессии в localStorage.