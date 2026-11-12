# 03 — Passport and lifecycle API

**Требования:** R13, R14, R15, R16, R17, R33, R34, R36, R41, R42, R43, R45, R46, R47, G01, G03, G04, G05, G06, G07, G08, G09, G15, G16, G17, G18, G19, G20, G21, G22, G23, A01 → R17
**Blocked by:** 02
**Зона:** `backend/apps/projects/`, `backend/apps/projects/api/`, `backend/config/`
**Волна:** 3
**Status:** ready

## Что должно заработать

Project lifecycle actions and passport API obey the approved state machine,
membership scope and executor/customer boundary. Concurrent passport edits
cannot overwrite a newer version.

## Из брифа, дословно

> “Add passport `version` handling and return `409 Conflict` for stale updates.”
>
> “Only the executor can update project metadata and passport directly.”
>
> “Оба участника сохраняют доступ ко всем данным проекта на чтение.”
>
> “`completed → active` — исполнитель может повторно открыть проект.”
>
> “После восстановления оно очищается.”

## Разделы спецификации

Истории 7–12, 14–18; Решения по реализации — «Модель и lifecycle»,
«Passport», «API»; Границы и швы — `projects`, `common`.

## Критерии приёмки

- [ ] Implement complete, reopen, archive and restore actions; only the executor can use them, only documented transitions succeed, invalid source states return 409, and archive/restore preserve and clear `status_before_archive` as specified.
- [ ] Completed and archived project, member and passport reads remain available to active members; project metadata and passport changes are rejected in read-only states.
- [ ] Passport GET returns the exact approved fields to executor and customer; PATCH accepts only those fields plus expected version and is available only to executor in `draft`/`active`.
- [ ] Version compare-and-update is atomic: current version persists changes and increments once; stale version returns 409 and leaves newer data intact. Invalid/missing fields return the common validation envelope.
- [ ] Complete, reopen, archive, restore and passport mutations write safe audit records within their transaction; project and document records are never deleted by archival.
- [ ] Metadata changes performed through the project CRUD API are also recorded via the shared audit writer; the complete A01 audit addition covers create, metadata, lifecycle and passport mutations.
- [ ] Tests cover each transition, actor/role violation, cross-project access, every project status, both passport readers, read-only errors and stale updates (including concurrent writes where the PostgreSQL test setup permits).
- [ ] OpenAPI accurately describes action/passport schemas and 409 responses; migrations remain additive and generated frontend types can be refreshed from the live schema.

## Границы

Use the domain services in `projects`, the shared error envelope and audit
writer. Do not add customer invitation acceptance, chat, documents,
questionnaire, Project State, retention jobs or any auto-deletion behavior.
