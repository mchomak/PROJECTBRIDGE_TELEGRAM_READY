# ADR 0005: Add the account user model without rewriting auth migrations

## Context

Stage 01 applied Django's `auth` migrations and the pgvector migration
before ProjectBridge had an account model. The local database's legacy
`auth_user` table is empty, and the existing ProjectBridge migration
history must remain intact.

## Decision

Configure `AUTH_USER_MODEL = "accounts.User"` and add
`accounts.0001_initial`, dependent on
`auth.0012_alter_user_first_name_max_length`. The migration creates the
custom user and email-verification token tables. Preserve
`common.0001_enable_pgvector`, all Django auth migrations, and the
legacy `auth_user` table unchanged on existing databases. Do not copy
users or reset the database. A clean database with the custom user model
configured before migrations does not create the legacy `auth_user`
table. Verify the migration on a separate empty PostgreSQL database and
on the existing local database.

New user relations use `settings.AUTH_USER_MODEL`.

## Why

An additive migration preserves the already-applied migration graph and
keeps standard Django auth tables available for permissions while the
application uses its email-based account model. The local table being
empty does not justify destructive schema changes.

## Consequences

The application account table is `accounts_user`. Existing databases
retain their unused legacy `auth_user` table; clean databases do not
create it. Account lifecycle and password reset behavior remain open
decisions and are not part of this change.
