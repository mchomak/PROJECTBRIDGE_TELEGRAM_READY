# ADR 0008: Browser Session Authentication and CSRF

## Context

The browser application and API operate as a same-origin client. Authentication must persist across visits without placing reusable session credentials in JavaScript-accessible persistent storage.

## Decision

Use Django session authentication with an HttpOnly session cookie. Protect every unsafe browser request, including anonymous authentication writes, with CSRF validation. The CSRF bootstrap provides the client token; production session and CSRF cookies are Secure, and both cookies use SameSite=Lax. The frontend does not persist session credentials in local storage.

## Why

A browser bearer-token design would require client-side storage and a separate token lifecycle, exposing reusable credentials to JavaScript. Cookie sessions keep the session credential HttpOnly and reuse Django's server-side session controls. Because browsers send cookies automatically, CSRF protection is part of this choice.

## Consequences

The frontend API boundary must send same-origin credentials and obtain a CSRF token before writes. Cross-origin browser clients require an explicit follow-up design; they are not enabled by this decision.