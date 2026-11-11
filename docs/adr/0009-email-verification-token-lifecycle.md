# ADR 0009: Email Verification Token Lifecycle

## Context

Email verification proves control of an address. Verification links are bearer credentials, so persisted records, retries, and delivery must limit the impact of database exposure and token replay.

## Decision

Generate a cryptographically random 256-bit token, store only its SHA-256 digest, and make it valid for 24 hours and one use. Resending replaces prior active tokens. Confirmation consumes the token atomically. Send the raw token only in the email link as a URL fragment; the frontend reads it once and removes it from the address bar before submitting it to the API. The application must not expose the raw token in API responses or separate application logs. The local console email backend displays the outbound message, including its link, as its delivery channel.

## Why

Storing the raw token would let a database reader use outstanding verification links. Reusable or non-expiring links would allow replay or retain value indefinitely. Putting the token in a query string or path would expose it to frontend server requests and their access logs; the fragment is not sent in the HTTP request.

## Consequences

Email delivery must receive the raw token while the database retains only its digest. The frontend must consume and clear the fragment promptly, and the backend must enforce expiration, single use, and atomic consumption.