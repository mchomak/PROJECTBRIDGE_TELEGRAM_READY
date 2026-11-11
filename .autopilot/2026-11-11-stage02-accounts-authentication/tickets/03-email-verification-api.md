# 03 — Email verification API

**Требования:** R09, R10, R11, R12, R13, R14, R18, R19, R35, R36, R39, R44, R45, R46, R52, R53, R59
**Blocked by:** 01
**Зона:** `backend/apps/accounts/api/verification/`, `backend/apps/accounts/api/verification_urls.py`, `backend/apps/accounts/tests/api/test_verification.py`
**Волна:** 2
**Status:** done

## Что должно заработать

Пользователь получает проверочное письмо, подтверждает адрес по одноразовой ссылке, либо безопасно просит новое письмо. Неверные, просроченные и повторно использованные токены не дают аккаунту ложного состояния verified и не раскрывают лишних сведений.

## Из брифа, дословно

> «email-verification resend, and verification confirmation.»
> «Generate high-entropy verification tokens, store only token hashes, enforce expiration and single use.»
> «Configure local console email delivery.»
> «Unverified accounts cannot be treated as email-verified.»
> «Email verification tokens expire and cannot be reused.»

## Разделы спецификации

Истории 8–10 и 12; Решения §6–8, §10–11; Границы §1–3.

## Критерии приёмки

- [ ] Реализованы `POST /api/v1/auth/email-verification/resend/` и `/confirm/` с OpenAPI request/response schemas.
- [ ] Resend отправляет письмо только существующему неподтверждённому аккаунту; не сообщает, существует ли email; аутентифицированная сессия может запросить письмо только для своего email.
- [ ] Confirm принимает raw token только в JSON body, успешно подтверждает в пределах TTL и атомарно помечает token использованным; повторный, просроченный или неизвестный token получает общий отказ.
- [ ] Письмо доставляется локальным console backend и содержит URL из `FRONTEND_BASE_URL` с token в URL fragment; API не возвращает raw token.
- [ ] Resend/confirm требуют CSRF, используют свои scoped throttle rates, возвращают 429 при превышении; ошибки не логируют raw token.
- [ ] Тесты покрывают send/resend, неизвестный email, verified account, authenticated email mismatch, CSRF, throttle, valid/expired/reused tokens, single use и verification timestamp.

## Ограничения

Не реализовывать password reset, смену email, учет ролей или другие account lifecycle flows.