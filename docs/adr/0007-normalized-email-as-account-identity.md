# ADR 0007: Normalized Email as Account Identity

## Context

Email is the account login identifier. Duplicate addresses must be rejected despite surrounding whitespace or case differences, and later email-bound workflows need to identify the same address consistently.

## Decision

Trim surrounding whitespace and apply Unicode casefold to the full email address before saving or comparing it. Use that normalized value for account identity, enforce uniqueness in both the service and database, and return the normalized address in the profile.

## Why

Preserving the original casing or folding only the domain would allow equivalent-looking addresses to form separate account identities, undermining duplicate prevention and future email-bound matching. The stage explicitly chooses deterministic full-address normalization over preserving case distinctions in the local part.

## Consequences

The original submitted casing is not retained as the canonical email value. Future features that bind records to email addresses must use the same normalization rule.