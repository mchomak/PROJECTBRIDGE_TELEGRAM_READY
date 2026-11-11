# ADR 0004: Persist local database and media with named volumes

## Context

The local Compose runtime must preserve database and uploaded-file data through ordinary container restarts.

## Decision

Store PostgreSQL data and uploaded media in named volumes. Routine `docker compose down` leaves those volumes intact; automatic destructive recovery is not part of startup.

## Why

Persistence across an ordinary restart is an explicit acceptance requirement, and the setup guide must not make routine startup or shutdown destructive.

## Consequences

Stopping and recreating containers preserves local data. Removing volumes must remain a deliberate reset operation rather than part of normal development commands.
