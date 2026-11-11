# Requirements Manifest

Source: `2026-11-11-brief.md`. Requirements remain live unless the user removes them.

| ID | Exact wording from the brief | Status | Basis | Where |
|---|---|---|---|---|
| R01 | “Inspect the existing repository, branches, current files, and the existing HTML MVP screen mockup.” | done | Repository has no Git metadata, dependency manifests, or app source; inspect the seed files and preserve the demo. | T0 single pass |
| R02 | “Preserve useful existing work. Treat the HTML mockup as a product/visual reference unless the repository already defines another role for it. Do not delete or overwrite it.” | done | ASSUMPTION — accepted on the user’s behalf: move the existing technical index into `docs/README.md`; leave the HTML mockup byte-for-byte unchanged at the root as a reference. | T0 single pass |
| R03 | “Establish the agreed monorepo layout: `frontend/`, `backend/`, `docs/`, `infra/`, `scripts/`.” | done | ASSUMPTION — accepted on the user’s behalf: create the five canonical top-level directories; use the nested documentation paths listed by the technical index and architecture. | T0 single pass |
| R04 | “Preserve the existing technical documentation under `docs/`. Do not regenerate or replace it.” | done | Move existing files within `docs/` into their documented locations without changing their contents; retain legacy and stage brief files. | T0 single pass |
| R05 | “Add or normalize root `.gitignore`.” | done | Git was absent; initialize `main` and ignore local-only files before adding new files. | T0 single pass |
| R06 | “Add or normalize `.env.example` with placeholders only.” | done | Use documented local configuration categories with obvious placeholder values; no credentials or provider-specific choice. | T0 single pass |
| R07 | “Add or normalize root `README.md` with local setup entry points.” | done | Create setup entry points and distinguish commands available now from those introduced with Stage 01. | T0 single pass |
| R08 | “Add or normalize repository scripts for common development commands, where useful.” | done | ASSUMPTION — accepted on the user’s behalf: no root scripts yet; there is no application/runtime command to wrap before Stage 01. | T0 single pass |
| R09 | “Inspect existing dependency manifests and lockfiles before choosing package managers or versions.” | done | Inspection found none. | T0 single pass |
| R10 | “Reuse established choices where sound; do not introduce a second package manager.” | done | ASSUMPTION — accepted on the user’s behalf: use npm with a committed npm lockfile for TypeScript and Python `venv` plus pip requirements for the backend when Stage 01 initializes dependencies. | T0 single pass |
| R11 | “Add baseline formatting, linting, and test configuration for Python and TypeScript only where compatible with the chosen toolchain.” | deferred | No application code, manifests, or established toolchain exists; add runnable configs with the Stage 01 apps. | spec §6 |
| R12 | “Ensure local secrets, database files, uploads, virtual environments, build output, and caches are ignored by Git.” | done | Cover secrets, SQLite, uploaded media, Python environments/caches, and frontend build/cache paths. | T0 single pass |
| R13 | “Repository structure matches `SYSTEM_ARCHITECTURE.md` or documented deviations are approved.” | done | Use the accepted nested docs map; add only top-level app/runtime placeholders in this stage. | T0 single pass |
| R14 | “No real secrets or local data are tracked by Git.” | done | Verify ignore rules and confirm no `.env`, database, or upload data exists in the baseline. | T0 single pass |
| R15 | “A new developer can identify how frontend and backend dependencies will be installed.” | done | Document npm and Python venv/pip entry points, clearly marked as available in Stage 01. | T0 single pass |
| R16 | “Root README links to the technical documentation and local-development instructions.” | done | Link to canonical `docs/README.md`, `docs/architecture/SYSTEM_ARCHITECTURE.md`, and `docs/operations/LOCAL_DEVELOPMENT.md`. | T0 single pass |
| R17 | “Formatting/lint/test commands are discoverable and run successfully for any initialized code.” | done | README lists planned frontend and backend format/lint/type-check/test commands, clearly marked unavailable until Stage 01 initializes the toolchains; no code exists in Stage 00 to check. | spec §5; T0 single pass |
| R18 | “No product feature has been implemented in this stage.” | done | Create placeholders and tooling notes only; no product code. | T0 single pass |
| R19 | “Reproducible dependency manifests and lockfiles, if dependencies are initialized at this stage.” | deferred | No dependencies are initialized; Stage 01 will add manifests and lockfiles alongside app code. | spec §6 |
| R20 | “Report the resulting repository tree and all setup commands.” | done | Include the final tree and commands in the completion report. | T0 single pass |
| G01 | “Забей на панель, просто закончи задачи” | done | User explicitly directed the run to skip opening the progress dashboard and finish Stage 00. | T0 single pass |

## Full-mode self-briefing decisions

- ASSUMPTION — accepted on the user’s behalf: the current technical index and `SYSTEM_ARCHITECTURE.md` define the canonical nested documentation paths; relocate existing documents without rewriting their contents.
- ASSUMPTION — accepted on the user’s behalf: npm is the frontend package manager; Python `venv` plus pip is the backend dependency entry point. Actual manifests and pinned dependencies belong with Stage 01 application initialization.
- ASSUMPTION — accepted on the user’s behalf: no generic root scripts or runnable lint/test/format configuration are useful before either application exists; document when they become available.
- ASSUMPTION — accepted on the user’s behalf: keep `projectbridge_mvp_demo.html` at the root unchanged as a visual/product reference.
- G1 passed 2026-11-11: all requirement rows have a status and no row remains open.
G3 passed 2026-11-11: all 19 in-spec requirements map to the one T0 single-pass assignment; no formal tickets are warranted.
