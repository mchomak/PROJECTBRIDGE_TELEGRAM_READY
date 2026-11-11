# 04 — Bind the frontend development port locally

**Requirements:** R24, R40
**Blocked by:** 03
**Zone:** `docker-compose.yml`
**Wave:** 4
**Status:** done

## What must work

The Compose frontend development server is reachable through the host's
localhost port without publishing the Vite port to other network interfaces.

## Specification sections

Local runtime; Local setup commands.

## Acceptance criteria

- [ ] The host mapping for port 5173 binds to `127.0.0.1`.
- [ ] `docker compose config --quiet` passes and Compose retains the frontend service health check.
- [ ] The frontend responds successfully through `http://localhost:5173/` after the service is recreated.
- [ ] Backend, database, Redis, and worker configuration is untouched.
