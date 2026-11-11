# Stage 00 — Repository Baseline and Tooling

**Goal:** Establish a clean, predictable monorepo foundation without
implementing product functionality.

## Read first

- `AGENTS.md`
- `docs/README.md`
- `docs/architecture/SYSTEM_ARCHITECTURE.md`
- `docs/operations/LOCAL_DEVELOPMENT.md`
- `docs/implementation/DEVELOPMENT_ROADMAP.md`

## Dependencies

None. This is the first implementation stage.

## Scope

1.  Inspect the existing repository, branches, current files, and the
    existing HTML MVP screen mockup.
2.  Preserve useful existing work. Treat the HTML mockup as a
    product/visual reference unless the repository already defines
    another role for it. Do not delete or overwrite it.
3.  Establish the agreed monorepo layout:
    - `frontend/`
    - `backend/`
    - `docs/`
    - `infra/`
    - `scripts/`
4.  Preserve the existing technical documentation under `docs/`. Do not
    regenerate or replace it.
5.  Add or normalize:
    - root `.gitignore`;
    - `.env.example` with placeholders only;
    - root `README.md` with local setup entry points;
    - repository scripts for common development commands, where useful.
6.  Inspect existing dependency manifests and lockfiles before choosing
    package managers or versions. Reuse established choices where sound;
    do not introduce a second package manager.
7.  Add baseline formatting, linting, and test configuration for Python
    and TypeScript only where compatible with the chosen toolchain.
8.  Ensure local secrets, database files, uploads, virtual environments,
    build output, and caches are ignored by Git.

## Out of scope

- Django domain models or API endpoints.
- React product pages or business features.
- Database schema and migrations.
- Authentication, projects, chat, documents, or AI implementation.
- Deployment infrastructure.

## Deliverables

- Agreed repository folder structure.
- Root setup instructions.
- `.env.example` without real secrets.
- `.gitignore`.
- Reproducible dependency manifests and lockfiles, if dependencies are
  initialized at this stage.
- Basic lint/test/format commands documented.

## Acceptance criteria

- [ ] Repository structure matches `SYSTEM_ARCHITECTURE.md` or
  documented deviations are approved.
- [ ] Existing HTML mockup and technical documentation are preserved.
- [ ] No real secrets or local data are tracked by Git.
- [ ] A new developer can identify how frontend and backend dependencies
  will be installed.
- [ ] Root README links to the technical documentation and
  local-development instructions.
- [ ] Formatting/lint/test commands are discoverable and run
  successfully for any initialized code.
- [ ] No product feature has been implemented in this stage.

## Stop conditions

Stop and report if the current repository already has a materially
different structure, an established package manager/toolchain, or
existing application code that would be damaged by the proposed layout.
Do not perform a destructive reorganization without approval.

## Codex handoff

Implement Stage 00 only. Inspect before editing, preserve existing
project work, and report the resulting repository tree and all setup
commands.
