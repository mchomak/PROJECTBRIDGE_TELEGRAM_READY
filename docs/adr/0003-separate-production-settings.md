# ADR 0003: Keep production settings separate from local defaults

## Context

The application needs local and test settings, while production startup must not inherit development-only configuration.

## Decision

Keep local, test, and production settings separate. Production defaults to `DEBUG=False`, requires an explicit non-local secret key and allowed hosts, rejects the local-only secret, and disables development API documentation.

## Why

The stage explicitly requires production-safe defaults and a separate local development configuration.

## Consequences

Production deployments must provide their own secret key and allowed hosts. Local placeholders and development documentation are not production configuration.
