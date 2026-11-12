# 04 — Project frontend

**Требования:** R01, R18, R19, R20, R21, R22, R23, R24, R25, R26, R35, R36, R42, R43, R47, R48, G01, G03, G04, G05, G06, G08, G09, G14, G15, G16, G17, G20, G21, G22, G23, G25
**Blocked by:** 03
**Зона:** `frontend/src/`, generated API types
**Волна:** 4
**Status:** ready

## Что должно заработать

The authenticated workspace becomes a project list, create flow, archive
view and project overview. Executor and customer see the same passport
data, with editing only where role and status allow it.

## Из брифа, дословно

> “Project list page.”
>
> “Project creation flow with the four project types.”
>
> “Project overview page.”
>
> “Passport view/edit experience for executor.”
>
> “Read-only passport view for customer once a customer membership exists.”
>
> “Loading, empty, validation, and error states.”

## Разделы спецификации

Истории 1–5, 7–13, 15, 17–18, 21–24; Решения по реализации — «Frontend»;
Границы и швы — Frontend project slices.

## Критерии приёмки

- [ ] Add protected project list, create, archived list and project overview routes; preserve existing authenticated-user checks and logout behavior.
- [ ] List screens distinguish ordinary and archived projects, show status, provide clear empty states, paginate through API results and never show a completion percentage.
- [ ] Create flow offers exactly the four project types, validates name/description, disables repeat submit while pending, retains input on failure and opens the created project on success.
- [ ] Overview shows project metadata, active participants, status-appropriate executor actions and the exact passport fields; executor edits only in `draft`/`active`, customer and all completed/archived views are read-only.
- [ ] Status actions update lists/detail caches and expose server state errors without inventing alternate transitions. Stale passport edits display conflict and allow explicit refresh while preserving unsaved form values until the user chooses reload.
- [ ] Loading, empty, validation, network and server error states are accessible and retryable where appropriate; keyboard, semantic form labels and responsive layout work.
- [ ] Frontend tests cover executor/customer permissions, list/archive views, create validation, passport edit/read-only, stale-version error and retry states; regenerate API types, then run format, lint, typecheck, tests and production build.

## Границы

Follow FSD downward dependencies and the shared API client. Do not edit
generated TypeScript types manually. Preserve the existing app language,
auth redirects, logout capability and unrelated screens.
