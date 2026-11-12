# Stage 03 — Implementation Interfaces

## Границы, решённые в спецификации

| Модуль | Владеет | Выставляет | Прячет |
|:--|:--|:--|:--|
| `projects` | Project, ProjectMember, ProjectPassport, project lifecycle и membership invariants | `create_project(*, actor, data) -> Project`; `complete_project(*, project_id, actor) -> Project`; `reopen_project(*, project_id, actor) -> Project`; `archive_project(*, project_id, actor) -> Project`; `restore_project(*, project_id, actor) -> Project`; selectors for member-scoped list/detail/members/passport; `update_passport(*, project_id, actor, expected_version, changes) -> ProjectPassport` | ORM mutation details, database constraints, transition validation, version compare-and-update; no Stage 03 invitation/member-acceptance workflow |
| `common` | ProjectAuditLog persistence and generic audit metadata writer | `record_project_action(*, project_id, actor_id, action, target_type, target_id, metadata) -> ProjectAuditLog` | audit model persistence details and safe metadata handling |
| Frontend project slices | Project queries, forms, lifecycle and passport interactions | typed query/mutation hooks consumed by pages | caching, request details and local mutation state |

**Тестовые швы:** `projects.services`/selectors for domain invariants,
`projects` REST API for auth/membership/role behavior, and React page/feature
boundaries for user states. Critical tests must use PostgreSQL for partial
unique constraints and transaction behavior; service/unit-level validation
may use the test runner's normal database.

## Проектные правила для этой реализации

- Implement only Stage 03 and the decisions in its spec. The docs sync
  requested before continuation is complete. Do not add invitation flow,
  questionnaire logic, Project State, progress, public-order import, or
  unrelated refactors.
- Preserve existing user changes and earlier Autopilot run artifacts.
  Change existing code only where required to integrate projects. Do not
  reset databases, replace migrations, or run `docker compose down -v`.
- Backend is Python 3.13.18, Django 5.2.19, DRF, PostgreSQL 17 with
  pgvector 0.8.7. Frontend is Node 24.22.2, React 19.3.1, TypeScript,
  Vite 8.3.7 and React Router 7; React feature dependencies follow FSD:
  `app -> pages -> widgets -> features -> entities -> shared`.
- PostgreSQL is the source of truth. Domain writes belong in owning-app
  services, reads in selectors, HTTP views remain thin. Enforce role and
  active-membership checks on the backend. Use additive migrations only.
- Use the current session and CSRF API client. Do not store credentials in
  browser storage. Generated API types come from OpenAPI and are not edited
  by hand.
- Do not install missing packages or change dependency manifests without a
  concrete requirement; report `BLOCKED` if an essential dependency is
  absent. Do not echo or modify `.env` secrets.
- No automatic deletion or retention schedule for completed/archived
  projects. Do not expose a completion percentage.

## Verified repository checks

Run from the repository root, using the existing Compose images and data:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps backend python manage.py makemigrations --check --dry-run
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
docker compose exec frontend npm run build
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
```

Backend source is baked into the image; after backend edits, rebuild/recreate
it with `docker compose up --build -d backend` before live schema or migration
checks. Apply migrations with `docker compose exec backend python manage.py
migrate`. Existing named volumes and local rows must remain intact.

## Из таска 01 — project persistence

- `Project` and `ProjectMember` are owned by `projects`; lifecycle values
  are `draft`, `active`, `completed`, `archived`; active memberships grant
  access. The database enforces membership uniqueness and archived-state
  consistency.
- `ProjectPassport` is one-to-one with Project, begins at version 1, and
  uses only the approved business fields. Decimal values currently use
  `max_digits=30`, `decimal_places=10` as an implementation assumption;
  `DATA_MODEL.md` leaves precision open.
- `create_project(*, actor, data) -> Project` atomically creates the draft,
  active executor membership and initial passport. It does not create a
  customer membership or accept invitations.
- `update_project_metadata(*, project_id, actor, changes) -> Project`
  updates allowed metadata and records its audit event in the same domain
  transaction. Metadata mutation rules live in `apps.projects.services`.
- `apps.projects.selectors` exposes member-scoped project list, detail and
  active-member queries; selectors do not perform writes.
- `record_project_action(*, project_id, actor_id, action, target_type,
  target_id, metadata) -> ProjectAuditLog` writes safe metadata; do not
  store field values, secrets or project contents.
- Additive migrations: `projects.0001_initial`,
  `projects.0002_project_constraints`, then
  `common.0002_project_audit_log`.

## Из таска 02 — project CRUD API

- `apps.projects.selectors.get_projects_for_member(*, user, status=None)`
  returns only active memberships; default excludes archived, `status="archived"`
  selects archive entries. Stable ordering is `updated_at DESC, id ASC`;
  page size defaults to 20 and is capped at 100.
- `apps.projects.selectors.get_project_for_member(*, project_id, user)`
  and `get_active_project_members(*, project_id)` are the member-scoped
  detail/member read boundaries. Inaccessible project reads return 404.
- `apps.projects.services.update_project_metadata(*, project_id, actor,
  changes) -> Project` validates executor role and `draft`/`active` state,
  updates the allowed metadata fields and records audit field names in one
  transaction.
- `GET, POST /api/v1/projects/`; `GET, PATCH
  /api/v1/projects/{project_id}/`; `GET
  /api/v1/projects/{project_id}/members/` provide list/create/detail/update/
  active-member reads. Project serializers reject client-supplied lifecycle
  fields and unknown fields.
- Project API schemas use standard page-number fields `count`, `next`,
  `previous`, `results` and the common error envelope. Verified email is
  required for creation; read access is scoped to active membership.


## ?? ????? 03 ? passport ? lifecycle API

- `complete_project(*, project_id, actor) -> Project`; valid only from `active`.
- `reopen_project(*, project_id, actor) -> Project`; valid only from `completed`.
- `archive_project(*, project_id, actor) -> Project`; valid from `draft`, `active`, and `completed`, recording `status_before_archive`.
- `restore_project(*, project_id, actor) -> Project`; restores the stored prior status and clears `status_before_archive`.
- `update_passport(*, project_id, actor, expected_version, changes) -> ProjectPassport` uses an atomic version compare-and-update; one successful write increments once, stale versions return 409 without data or audit mutation.
- `get_passport_for_member(*, project_id, user)` allows active project members to read in every status.
- `POST /api/v1/projects/{project_id}/complete/`, `/reopen/`, `/archive/`, and `/restore/`; each action is executor-only.
- `GET, PATCH /api/v1/projects/{project_id}/passport/`; PATCH accepts a positive `version` and at least one approved passport field, requires executor role and `draft`/`active` status.
- Lifecycle and passport writes record safe audit events in their transaction. Invalid source states and read-only writes return 409; all access remains scoped to active membership.


## ?? ????? 04 ? project frontend

- `getProjects(archived: boolean, page: number) -> Promise<ProjectPage>`; `getProject(projectId: string) -> Promise<Project>`; `getProjectMembers(projectId: string) -> Promise<ProjectMember[]>`; `getProjectPassport(projectId: string) -> Promise<ProjectPassport>`.
- Query hooks: `useProjectList(archived, page)`, `useProject(projectId)`, `useProjectMembers(projectId)`, `useProjectPassport(projectId)`; each returns the inferred TanStack Query result with `Error` errors.
- Mutations: `useCreateProject()` with `ProjectCreate`; `useUpdateProject(projectId)` with `ProjectMetadataUpdate`; `useProjectLifecycleAction(projectId)` with `LifecycleAction = 'complete' | 'reopen' | 'archive' | 'restore'`; `useUpdatePassport(projectId)` with generated `ProjectPassportPatchSchema` (`version` required).
- Protected routes: `/app` redirects to `/app/projects`; child routes `/app/projects`, `/app/projects/archive`, `/app/projects/new`, `/app/projects/:projectId`.
- Project REST requests use the shared same-origin CSRF API client; generated OpenAPI types are refreshed by the existing API type-generation script and are never edited manually.
