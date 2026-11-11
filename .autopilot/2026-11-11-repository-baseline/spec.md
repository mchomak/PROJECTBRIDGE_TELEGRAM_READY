# Specification: Stage 00 — Repository Baseline and Tooling

## 1. Current baseline

The workspace is not yet a Git repository. It contains the project instructions, a technical-document index currently at the root, technical documents stored flat under `docs/`, implementation stage briefs, a legacy DOCX, VS Code settings, and `projectbridge_mvp_demo.html`. There are no frontend or backend source applications, dependency manifests, lockfiles, or established package managers.

The existing HTML file is an interactive local demo with browser-local persistence. It remains a reference and must not be rewritten, moved, or incorporated as the Stage 00 frontend application.

## 2. Repository structure and documentation

Initialize Git on `main` and create the top-level `frontend/`, `backend/`, `docs/`, `infra/`, and `scripts/` directories. Empty app/runtime directories use `.gitkeep` until Stage 01 creates the applications and local runtime.

The technical architecture and the existing documentation index specify a nested documentation layout. Relocate the existing files within `docs/` to those canonical paths without editing their technical content:

- `docs/README.md` — move the current root technical-document index here.
- `docs/product/MVP_SCOPE.md`.
- `docs/architecture/{SYSTEM_ARCHITECTURE,FRONTEND_ARCHITECTURE,BACKEND_ARCHITECTURE}.md`.
- `docs/database/DATA_MODEL.md` and `docs/api/API_CONTRACT.md`.
- `docs/ai/AI_ARCHITECTURE.md`, `docs/security/ACCESS_CONTROL_AND_SECURITY.md`, and `docs/documents/DOCUMENT_LIFECYCLE.md`.
- `docs/operations/LOCAL_DEVELOPMENT.md`.
- `docs/decisions/ADR-001…ADR-008`.
- `docs/implementation/DEVELOPMENT_ROADMAP.md`, retaining all stage briefs beneath `docs/implementation/stages/`.
- Keep `docs/OPEN_DECISIONS.md` and the existing `docs/legacy/` content in place.

The new root `README.md` becomes local setup entry points and links to the technical index, architecture, and local development guide. Do not alter or remove `projectbridge_mvp_demo.html`.
### Boundaries and test seams

The repository baseline owns root setup configuration and empty top-level application/runtime directories. `docs/` owns the technical documents; this stage may relocate them within `docs/` to match the accepted index but must not edit their technical content. `projectbridge_mvp_demo.html` is read-only. No runtime modules or public signatures are introduced. The verification seam is the Git/filesystem boundary: expected paths, Markdown links, ignore behavior, and unchanged SHA-256 hashes for the mockup and moved documentation.

## 3. Dependency installation choices

Inspection found no package manifests or lockfiles, so there is no established toolchain to reuse. ASSUMPTION — accepted on the user’s behalf: use npm with a committed `package-lock.json` for the TypeScript frontend, and Python’s built-in `venv` plus pip requirements for the backend. Stage 00 does not create either app’s dependencies; Stage 01 will add the manifests, pinned versions, and locks with the runnable application skeleton.

The README names the future install entry points:

- Frontend: run `npm ci` from `frontend/` after Stage 01 adds `package.json` and `package-lock.json`.
- Backend: from `backend/`, create `.venv`, activate it, then run `python -m pip install -r requirements.txt` after Stage 01 adds the pinned requirements file.

Do not claim these app install/start/test commands work before those files exist. No second package manager is introduced for either language.

## 4. Environment and Git exclusions

Create `.env.example` with only explicit placeholders for local Django, database, Redis, frontend, file-storage, console-email, and generic AI provider configuration. Do not include credentials or select an AI vendor.

Normalize `.gitignore` to exclude `.env` and `.env.*` while allowing `.env.example`, Python environments and caches, Node modules, build output, SQLite/database files, local uploaded media, coverage output, logs, and the Autopilot local server state. The progress-dashboard files remain outside this user's requested implementation concern; do not open the dashboard.

## 5. Setup instructions and development commands

The root README must:

- explain that Stage 00 is repository setup and that React/Django applications and Docker Compose arrive in Stage 01;
- link to `docs/README.md`, `docs/architecture/SYSTEM_ARCHITECTURE.md`, and `docs/operations/LOCAL_DEVELOPMENT.md`;
- show the `.env.example` copy step and identify where frontend/backend dependencies will be installed;
- list planned format, lint, type-check, and test commands for each app, clearly marked as Stage 01 commands that are not runnable until their manifests, dependencies, and source code exist;
- state which commands are not available yet because no app manifests or source code exist.

No root scripts are added: there is no common runnable application command to wrap at this stage. No lint, format, type-check, or test config is added without initialized code/toolchains; Stage 01 adds these alongside the apps and documents the commands named in the README. This is a scoped deferral, not a claim that empty code passed checks. Planned command names: from `frontend/`, `npm run format:check`, `npm run lint`, `npm run typecheck`, and `npm test`; from `backend/`, `ruff format --check .`, `ruff check .`, and `python -m pytest`.

## 6. Out of scope and acceptance

| Requirement | Why not in Stage 00 |
|---|---|
| R11 — runnable Python/TypeScript formatting, lint, and test configuration | No application source, manifests, or established compatible toolchain exists; configure with Stage 01. |
| R19 — reproducible dependency manifests and lockfiles | No dependencies are initialized in this stage; create them with Stage 01 app manifests. |

No Django/React application code, domain models, API endpoints, migrations, authentication, product workflows, or deployment configuration are added. Stage 00 finishes with setup documentation, environment placeholders, ignore rules, canonical folders, and the existing technical content and demo preserved.

The user’s follow-up is followed literally: do not open the Autopilot progress dashboard; finish the repository work and report the result.

## 7. Manifest coverage

| Requirement | Coverage |
|---|---|
| R01 | §1, inspect current files and Git state. |
| R02 | §§1–2, retain the HTML file unchanged and keep it as a reference. |
| R03 | §2, create the five top-level directories. |
| R04 | §2, relocate technical documents without editing their content. |
| R05 | §2 and §4, initialize Git and normalize `.gitignore`. |
| R06 | §4, placeholder-only `.env.example`. |
| R07 | §2 and §5, new root setup README. |
| R08 | §5, choose no scripts because there is no runnable command to wrap. |
| R09 | §§1 and 3, record that manifests/locks were inspected and absent. |
| R10 | §3, npm plus Python venv/pip; no second manager per ecosystem. |
| R11 | §6, explicitly deferred until app code exists. |
| R12 | §4, ignore local secrets, data, environments, outputs, and caches. |
| R13 | §2, follow the documented architecture paths. |
| R14 | §4, placeholder-only environment sample and local-data exclusions. |
| R15 | §§3 and 5, identify future frontend and backend install commands. |
| R16 | §5, link root README to canonical technical docs. |
| R17 | §5, list planned frontend and backend format/lint/type-check/test commands and mark them unavailable until Stage 01 initializes the toolchains. |
| R18 | §6, no product functionality. |
| R19 | §6, explicitly deferred because no dependencies are initialized. |
| R20 | §5 and final report, provide setup commands and tree. |
| G01 | §6, skip dashboard opening and finish Stage 00. |
