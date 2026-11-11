# ADR 0002: Generate frontend API types from OpenAPI

## Context

The backend exposes an API schema and the frontend needs types that reflect the API contract.

## Decision

Expose the development schema at `/api/schema/` with drf-spectacular and generate TypeScript declarations from it into the frontend's generated API directory. Do not hand-edit generated endpoint or response types.

## Why

The schema is the shared contract between the Django API and the frontend. Generation avoids a second manually maintained copy of endpoint types.

## Consequences

Type generation requires a reachable schema endpoint and exits with an error when it cannot fetch the schema. Generated declarations must be refreshed from the schema instead of edited directly.
