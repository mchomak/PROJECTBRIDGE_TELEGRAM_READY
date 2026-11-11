# ADR 0001: Single ASGI entry point for HTTP and WebSocket

## Context

Stage 01 needs a Django HTTP readiness endpoint and a WebSocket probe, while the project remains a modular monolith.

## Decision

Use `config.asgi.application` to compose Django HTTP with the Channels WebSocket router. Configure the Channels layer through Redis.

## Why

The stage requires one ASGI application for both protocols and a Redis-backed Channels layer. The WebSocket route proves infrastructure only; it does not define chat or membership behavior.

## Consequences

Both HTTP and WebSocket startup depend on the ASGI configuration. Redis is required by the local runtime for the channel layer, and `/ws/v1/health/` remains an operational probe.
