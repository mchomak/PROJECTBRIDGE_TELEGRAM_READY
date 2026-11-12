# 02 — Project API

**Требования:** R05, R08, R09, R10, R11, R12, R34, R37, R39, R40, R41, R44, R45, G14, G15
**Blocked by:** 01
**Зона:** `backend/apps/projects/`, `backend/apps/projects/api/`, `backend/config/`
**Волна:** 2
**Status:** ready

## Что должно заработать

Verified authenticated executor can create a project; active members can
list, open and inspect participants. The API limits every query to active
membership and enforces executor-only metadata writes.

## Из брифа, дословно

> “Support the four initial project types only: `website`, `telegram_bot`, `automation`, `other`.”
>
> “Implement project list, create, detail, update, member list, complete, and archive operations described in the API contract.”
>
> “A verified authenticated user can create a project.”
>
> “A user sees only projects where they are an active member.”

## Разделы спецификации

Истории 1–6, 13–15, 21–24; Решения по реализации — «API»; Границы и швы —
`projects`.

## Критерии приёмки

- [ ] Register list, create, detail, metadata PATCH and active-member list endpoints under `/api/v1/projects/` with drf-spectacular request/response/error schemas.
- [ ] Anonymous requests return the shared 401 envelope; unverified creation and customer metadata writes are denied; nonmembers cannot read another project (404).
- [ ] List returns only active-member projects, excludes archived by default, returns only archived for `?status=archived`, validates other status filters, and uses page-number pagination with the specified stable ordering/bounds.
- [ ] Create accepts only the four types, requires a valid name, permits optional description, calls the atomic domain service, and returns 201 with the created draft project.
- [ ] Detail and member-list reads work for both active project roles; inactive or foreign membership never leaks project or participant data.
- [ ] Metadata PATCH accepts only name/type/description and only for executor membership in `draft`/`active`; customer, completed and archived writes are rejected, and server-owned status fields are not writable.
- [ ] API tests cover verified/unverified access, role and cross-project boundaries, enum/name validation, archive filtering, pagination and audit logging; project migrations and types remain in sync.

## Границы

Use the project selectors/services from `interfaces.md`; views only perform
HTTP orchestration. This ticket owns member-scoped project selectors, the
metadata update service, CRUD/read API surface and API tests. Lifecycle
actions and passport endpoints belong to ticket 03. Domain rules and audit
writes stay in `apps.projects.services`, never an API-local service layer.
