# Local Development and Operations

**Status:** Current local MVP runtime

**Last updated:** 2026-11-13

## Scope and pinned runtime

Docker Compose runs the local ProjectBridge MVP. Email uses Django's console backend; follow
`docker compose logs -f backend` to see locally generated messages.

| Service | Image or runtime | Local access |
|:--|:--|:--|
| `frontend` | `node:24.22.2-alpine3.23` | `http://localhost:5173` |
| `backend` | `python:3.13.18-slim-bookworm` | `http://localhost:8000` |
| `db` | `pgvector/pgvector:0.8.7-pg17-bookworm` | Compose network only |
| `redis` | `redis:7.4.12-alpine3.21` | Compose network only |
| `celery-worker` | `python:3.13.18-slim-bookworm` | Compose network only |
| `celery-beat` | `python:3.13.18-slim-bookworm` | Compose network only |

Host ports 5173 and 8000 must be available before startup. The backend
host port defaults to 8000 and can be changed with `BACKEND_HOST_PORT`
in `.env`; use the configured port for direct backend URLs below. This
workspace uses 8001 because another local service already occupies 8000.

PostgreSQL data and uploaded media use the named volumes
`projectbridge_postgres_data` and `projectbridge_media`. PostgreSQL and
Redis ports are not published to the host. The example database and
Redis passwords, and Django local key, are development placeholders;
never use them in a deployed environment or commit a real `.env` file.

Celery Beat recovers stale document-processing, AI-analysis, and
specification-generation dispatches every 60 seconds. It also processes due
mutual-consent document deletions every five minutes. Redis is the broker; the
owning app keeps durable request status, publish outcomes, and dispatch leases
in PostgreSQL. After five publish exceptions, `queue_unavailable` reports that
the queued work is waiting for processing and automatic retries continue with
30-second to 30-minute exponential backoff with a stored exception-count cap
of 12. After five dispatch reservations
without a worker claim, `worker_backlog` reports delayed worker pickup. Both
warnings are nonterminal and clear when a worker claims the operation. Publish
exceptions are ambiguous, so recovery keeps the same task ID for the queued
operation and never invalidates older FIFO copies.

## PowerShell setup

Run from the repository root. Create `.env` only once so an existing
local configuration is not overwritten:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose ps
docker compose logs -f
```

Use `Ctrl+C` to stop following logs; this leaves the services running.
The POSIX setup is the same except the first command is
`test -f .env || cp .env.example .env`.

## POSIX setup

Run from the repository root:

```sh
test -f .env || cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f
```

Use `Ctrl+C` to stop following logs; this leaves the services running.

## Start, inspect, and stop

The following Docker commands work unchanged in PowerShell and POSIX
shells from the repository root:

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose logs -f backend celery-worker
docker compose exec backend python manage.py migrate
docker compose down
```

`docker compose ps` should show all six services as healthy. The final
command stops containers but preserves both named data volumes. Do not
add `-v` when stopping during routine work or persistence verification.

## Quality checks

Run the backend checks inside the pinned Python image from either shell:

```sh
docker compose run --rm --no-deps backend ruff format --check .
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest
```

Run the frontend checks inside the pinned Node image:

```sh
docker compose exec frontend npm run format:check
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

## Runtime checks

First check container health and the frontend/backend health endpoints.
These examples return the HTTP status and health JSON respectively.

PowerShell:

```powershell
$backendHostPort = (Select-String -Path .env -Pattern '^BACKEND_HOST_PORT=').Line.Split('=')[1]
(Invoke-WebRequest -Uri http://localhost:5173/ -UseBasicParsing).StatusCode
Invoke-RestMethod "http://localhost:$backendHostPort/api/v1/health/"
Invoke-RestMethod http://localhost:5173/api/v1/health/
```

macOS/Linux:

```sh
BACKEND_HOST_PORT="$(sed -n 's/^BACKEND_HOST_PORT=//p' .env | tr -d '\r')"
curl --fail --show-error --output /dev/null --write-out '%{http_code}\n' http://localhost:5173/
curl --fail --show-error "http://localhost:${BACKEND_HOST_PORT}/api/v1/health/"
curl --fail --show-error http://localhost:5173/api/v1/health/
```

Both health requests should report `status: ok` and database and Redis
dependencies as `ok`; the frontend health request confirms the Vite HTTP
proxy. The frontend root should return HTTP 200.

Check the pgvector extension after migrating. These commands use the
database defaults in `.env.example`; adjust the database/user arguments
if you changed `DB_NAME` or `DB_USER`:

```sh
docker compose exec backend python manage.py migrate
docker compose exec db psql -U projectbridge -d projectbridge -Atc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

The query prints `vector` when the migration has enabled the extension.

Submit the operational task through the real worker. Local settings set
`CELERY_TASK_ALWAYS_EAGER=False`; this command enqueues through Redis and
waits for the worker's result:

```sh
docker compose exec backend python -c "from config.celery_app import app; from apps.common.tasks import runtime_probe; result = runtime_probe.delay(); value = result.get(timeout=20); print(value); assert value == {'status': 'ok'}"
```

The result should be `{'status': 'ok'}`. The worker health check also
uses Celery `inspect ping` and should show healthy in `docker compose ps`.

Check the backend schema and interactive docs directly and through Vite.
PowerShell:

```powershell
$backendHostPort = (Select-String -Path .env -Pattern '^BACKEND_HOST_PORT=').Line.Split('=')[1]
(Invoke-WebRequest -Uri "http://localhost:$backendHostPort/api/schema/" -UseBasicParsing -Headers @{ Accept = 'application/vnd.oai.openapi+json' }).StatusCode
(Invoke-WebRequest -Uri "http://localhost:$backendHostPort/api/docs/" -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri http://localhost:5173/api/schema/ -UseBasicParsing -Headers @{ Accept = 'application/vnd.oai.openapi+json' }).StatusCode
(Invoke-WebRequest -Uri http://localhost:5173/api/docs/ -UseBasicParsing).StatusCode
```

macOS/Linux:

```sh
BACKEND_HOST_PORT="$(sed -n 's/^BACKEND_HOST_PORT=//p' .env | tr -d '\r')"
curl --fail --show-error --output /dev/null --write-out '%{http_code}\n' --header 'Accept: application/vnd.oai.openapi+json' "http://localhost:${BACKEND_HOST_PORT}/api/schema/"
curl --fail --show-error --output /dev/null --write-out '%{http_code}\n' "http://localhost:${BACKEND_HOST_PORT}/api/docs/"
curl --fail --show-error --output /dev/null --write-out '%{http_code}\n' --header 'Accept: application/vnd.oai.openapi+json' http://localhost:5173/api/schema/
curl --fail --show-error --output /dev/null --write-out '%{http_code}\n' http://localhost:5173/api/docs/
```

All four requests should return HTTP 200. Generate types from the live
Compose schema endpoint; this command works in PowerShell and POSIX
shells, and writes `src/shared/api/generated/schema.d.ts` in the
frontend container:

```sh
docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types
docker compose exec frontend node --input-type=module -e "import { stat } from 'node:fs/promises'; const result = await stat('src/shared/api/generated/schema.d.ts'); if (result.size === 0) process.exit(1); console.log(result.size + ' bytes');"
```

The generation command exits nonzero and prints its source URL if the
schema endpoint cannot be fetched.

Verify the WebSocket upgrade through Vite. Node 24's built-in WebSocket
client connects to Vite at `ws://localhost:5173/ws/v1/health/`; Vite
proxies the upgrade to Django. The command succeeds only after receiving
the expected JSON and a normal close code (`1000`):

```sh
docker compose exec frontend node --input-type=module -e "const ws = new WebSocket('ws://localhost:5173/ws/v1/health/'); let received = false; const timeout = setTimeout(() => process.exit(1), 5000); ws.addEventListener('message', (event) => { let payload; try { payload = JSON.parse(event.data); } catch { process.exit(1); } if (payload.status !== 'ok') process.exit(1); received = true; console.log(JSON.stringify(payload)); }); ws.addEventListener('close', (event) => { clearTimeout(timeout); console.log('close code=' + event.code); process.exit(received && event.code === 1000 ? 0 : 1); }); ws.addEventListener('error', () => { clearTimeout(timeout); process.exit(1); });"
```

## Persistence verification

Seed one harmless Django auth-group row and one uploaded-media volume
marker, then restart without removing volumes. These commands work in
PowerShell and POSIX shells:

```sh
docker compose exec backend python manage.py shell -c "from django.contrib.auth.models import Group; Group.objects.update_or_create(name='compose-persistence-probe'); print('database marker seeded')"
docker compose exec backend python -c "from pathlib import Path; Path('/app/media/compose-persistence-probe.txt').write_text('projectbridge media persistence marker'); print('media marker seeded')"
docker compose down
docker compose up --build -d
docker compose ps
docker compose exec backend python manage.py shell -c "from django.contrib.auth.models import Group; assert Group.objects.filter(name='compose-persistence-probe').exists(); print('database marker persisted')"
docker compose exec backend python -c "from pathlib import Path; path = Path('/app/media/compose-persistence-probe.txt'); assert path.read_text().strip() == 'projectbridge media persistence marker'; print('media marker persisted')"
```

Do not use `docker compose down -v`; it deletes the volumes this check is
meant to preserve. Leave the stack running after this verification so
the local runtime is ready to use.
