# ADR 0006: Dedicated UUID Email User Model

## Context

ProjectBridge accounts need a durable UUID identity and email-based authentication. Email verification state belongs to the account, while first and last names are optional.

## Decision

Represent each account with a dedicated accounts.User model using a UUID primary key and email as its unique login identifier. Keep optional profile fields on that same model.

## Why

A separate profile layered over Django's auth.User would leave authentication identity and account-specific state split across two records, and would retain the built-in model's identity shape. A dedicated model provides one account identity for authentication and later project relationships.

## Consequences

Authentication and account state share one UUID-backed record. Code that refers to an account uses this model as the account identity rather than treating profile data as a separate identity.