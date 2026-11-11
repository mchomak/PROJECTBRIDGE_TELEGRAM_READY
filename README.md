# ProjectBridge

ProjectBridge is a collaborative project workspace for executors and
customers. This repository is at Stage 00: the monorepo layout and setup
entry points are being established. The React frontend, Django backend,
and Docker Compose runtime are introduced in Stage 01.

## Local setup

Copy the environment template before configuring a local environment:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux, use `cp .env.example .env`.

The template contains placeholders only. Replace them with local values
when Stage 01 adds the applications and their configuration.

### Frontend dependencies

After Stage 01 adds `frontend/package.json` and
`frontend/package-lock.json`, install frontend dependencies from
`frontend/` with:

```sh
cd frontend
npm ci
```

This command is **not yet runnable** because those manifest files do not
exist yet.

### Backend dependencies

After Stage 01 adds the pinned `backend/requirements.txt`, create and
activate a virtual environment in `backend/`, then install dependencies.
In PowerShell:

```powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux:

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The complete sequences are **not yet runnable** because the requirements
file and backend application do not exist yet.

## Planned quality commands (Stage 01; not runnable yet)

These are the planned quality checks for the initialized applications.
They are not available or runnable yet because application source,
manifests, dependencies, and tool configuration do not exist. Stage 01
will add those files and make these commands runnable.

Frontend commands, run from `frontend/`:

```sh
npm run format:check
npm run lint
npm run typecheck
npm test
```

Backend commands, run from `backend/`:

```sh
ruff format --check .
ruff check .
python -m pytest
```

No application start commands are available yet either; Stage 01 adds
the React and Django applications and their local runtime.

## Technical documentation

- [Technical documentation index](docs/README.md)
- [System architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Local development guide](docs/operations/LOCAL_DEVELOPMENT.md)

The existing [HTML mockup](projectbridge_mvp_demo.html) remains a local
product and visual reference.
