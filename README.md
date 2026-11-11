# ProjectBridge

ProjectBridge is a collaborative workspace for executors and customers.
The repository now contains the Stage 01 application skeleton and local
runtime: React/Vite, Django/ASGI, PostgreSQL with pgvector, Redis, and a
Celery worker. Stage 01 adds infrastructure and operational probes only;
it does not add product workflows or business models.

## Local runtime

Prerequisites are Docker Engine or Docker Desktop with Docker Compose.
Create the local environment file and start the pinned runtime from the
repository root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose ps
```

The `Copy-Item` command is `cp .env.example .env` in macOS/Linux shells.
Use [the local development guide](docs/operations/LOCAL_DEVELOPMENT.md)
for migrations, tests, health and proxy checks, type generation, and
persistence verification. Stop with `docker compose down`; named data
volumes are preserved.

## Documentation

- [Technical documentation index](docs/README.md)
- [System architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Local development guide](docs/operations/LOCAL_DEVELOPMENT.md)
- [Stage 01 brief](docs/implementation/stages/01-application-skeleton-and-local-runtime.md)
- [HTML product reference](projectbridge_mvp_demo.html)
