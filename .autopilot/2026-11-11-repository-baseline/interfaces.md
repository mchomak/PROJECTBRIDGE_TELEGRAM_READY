# Interfaces and implementation rules

## Boundaries, resolved in the specification

- Repository setup owns the root `.gitignore`, `.env.example`, setup `README.md`, and the top-level empty application/runtime directories.
- `docs/` owns the technical documents. Move them only within `docs/` to the canonical paths listed in the specification; do not change technical prose.
- `projectbridge_mvp_demo.html` is an immutable product/visual reference.
- No app modules or public code signatures are introduced in Stage 00.
- Verification seam: repository paths, Markdown link targets, `git check-ignore`, and before/after SHA-256 comparisons for the mockup and existing documentation.

## Repository rules for this assignment

- Target stack from the architecture: React + TypeScript + Vite and Python + Django/DRF. No application code or dependencies exist yet.
- Assumed future dependency entry points: npm with `package-lock.json`; Python `venv` plus pinned pip requirements. Stage 01 owns actual manifests, versions, and locks.
- Do not install dependencies or introduce additional package managers.
- Do not add product features, app source, database schema, migrations, Docker Compose, or deployment configuration.
- Do not edit existing technical document contents. The current root README is the existing technical index: relocate it to `docs/README.md`, then create a new root setup README.
- No runnable lint/format/test setup is possible before apps and manifests exist. Document this deferral; do not claim a check ran.
- Do not open or update the progress dashboard. The user explicitly asked to skip it.

## Commands

No application commands are runnable in Stage 00. The root README records these planned Stage 01 commands so the quality workflow is discoverable before the applications exist:

- Frontend dependencies: `npm ci` from `frontend/` after the package and lock files exist.
- Backend dependencies: create and activate a Python virtual environment in `backend/`, then run `python -m pip install -r requirements.txt` after the pinned requirements file exists.
- Frontend quality checks from `frontend/`: `npm run format:check`, `npm run lint`, `npm run typecheck`, and `npm test`.
- Backend quality checks from `backend/`: `ruff format --check .`, `ruff check .`, and `python -m pytest`.

The quality commands are planned interfaces, not runnable checks in Stage 00. Stage 01 owns the package scripts, tool dependencies, and compatible configurations; no tests or package scripts should be added until it creates app code.
