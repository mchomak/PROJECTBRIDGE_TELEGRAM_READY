# ADR-003: Use Feature-Sliced Design for the Frontend

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

The frontend will gain additional screens and features after the MVP. A
feature-oriented structure is needed to keep dependencies understandable
as the application grows.

## Decision

Use React, TypeScript, and Vite with Feature-Sliced Design layers:

- `app`
- `pages`
- `widgets`
- `features`
- `entities`
- `shared`

Dependencies flow downward. Higher layers compose lower layers; lower
layers do not import from higher layers.

## Consequences

- Route-level composition remains separate from reusable business
  features.
- Domain entities have a clear place in the codebase.
- Generic UI and infrastructure are centralized in `shared`.
- Avoid circular imports and cross-layer shortcuts.
- TanStack Query manages server state; local React state handles
  transient UI state.
- Redux/Zustand are not added without a demonstrated need.
