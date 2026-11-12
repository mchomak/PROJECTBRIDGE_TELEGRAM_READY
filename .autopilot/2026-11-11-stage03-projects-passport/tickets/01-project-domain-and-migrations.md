# 01 — Project domain and migrations

**Требования:** R04, R06, R07, R32, R38, R44, R46, R47, G01, G22, G23
**Blocked by:** —
**Зона:** `backend/apps/projects/`, `backend/apps/common/`
**Волна:** 1
**Status:** ready

## Что должно заработать

Project, membership и passport хранят утверждённую модель данных. Вызов
доменных сервисов атомарно создаёт черновик, executor membership и
начальный паспорт. Невалидное состояние не проходит ограничения БД, а
security-relevant project mutations получают безопасные audit records.

## Из брифа, дословно

> “Implement Project, ProjectMember, and ProjectPassport models and migrations.”
>
> “Create Project, executor membership, and passport atomically.”
>
> “Не добавляем самостоятельно новые бизнес-поля.”
>
> “Не меняй существующий код и ранее созданные материалы прогона без необходимости.”

## Разделы спецификации

Истории 1, 6, 6a, 9a, 10, 18–21, 25; Решения по реализации — «Модель и lifecycle»,
«Passport»; Границы и швы — `projects`, `common`.

## Критерии приёмки

- [ ] Additive migrations define Project, ProjectMember and ProjectPassport with UUID keys, exact fields, four project types, four lifecycle statuses and the documented timestamps.
- [ ] Constraints enforce one row per `(project, user)`, one active member per `(project, role)`, valid roles/statuses and coherent archived/previous-status/timestamp values; only active membership grants access.
- [ ] Passport has exactly the approved business fields, starts at version 1, and uses the documented empty/null initial values without introducing business requiredness.
- [ ] `create_project` runs in one transaction and creates Project (`draft`), executor membership and passport together; a failure rolls all three back.
- [ ] `common.ProjectAuditLog` follows `DATA_MODEL.md`; the safe writer records project creation without field values, credentials or sensitive content, inside the same transaction.
- [ ] Tests cover model constraints, failed atomic create rollback, initial passport defaults, and audit metadata safety; migrations are additive and pass the migration check.

## Границы

Do not implement invitation acceptance or customer-member creation. Keep
the service signatures in `interfaces.md`; only the Stage 03 project create
operation is implemented in this ticket. Preserve pre-existing source and
run artifacts outside the assigned zone unless a required integration
demonstrably needs a change.
