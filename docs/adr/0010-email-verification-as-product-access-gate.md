# ADR 0010: Email Verification as a Product Access Gate

## Context

Registration creates an account before ownership of its email address is proven. Users still need to reach the verification flow. Stage 02 has a frontend /app route but introduces no product APIs.

## Decision

Allow an unverified user to log in only to continue verification. Registration and successful verification do not create a session; the user logs in explicitly after confirming the address. In Stage 02, frontend route guards block /app for unverified accounts. When product APIs are introduced, their backend authorization must also require verified email.

## Why

Blocking all login until verification would prevent an unverified user from using authenticated verification steps. Automatically creating a session at registration or confirmation would couple verification to authentication and remove the explicit login transition. Relying on frontend guards alone for future product APIs would leave API access unenforced.

## Consequences

Stage 02 enforces the product-route gate in the frontend only; no product APIs exist in this stage. Future product APIs must check verification on the backend, and clients must handle an authenticated but unverified user.