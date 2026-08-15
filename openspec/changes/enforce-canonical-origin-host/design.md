## Context

`kavex.ir` resolves to ArvanCloud edge addresses, while `http://130.185.75.68/` reaches the Ubuntu Nginx origin directly. Live inspection on 2026-07-26 showed that the canonical domain, origin IP, `www`, and an arbitrary Host all returned HTTP 200 with the same Next.js ETag. The different screenshots therefore represent separate host state or cache, not separate source revisions.

## Goals / Non-Goals

- Goals: make the configured canonical domain (currently `https://kavehmetal.com`) the only storefront origin, preserve deep links, prevent unsafe cross-host request replay, and detect a regression during deployment.
- Non-goals: change DNS/CDN configuration, install an origin TLS certificate, or rewrite the unknown production Nginx virtual-host files automatically.

## Decisions

### Application-level host guard

Next.js middleware runs before static/ISR route resolution, so it also protects cached homepage responses. It compares the raw `Host` header with the configured canonical origin. The raw Host takes precedence over `X-Forwarded-Host` so a direct client cannot bypass the policy by supplying a forwarded header.

### Redirect and rejection semantics

GET and HEAD requests receive HTTP 301 and retain both path and query. Other methods receive HTTP 421 because a permanent redirect could change the method or replay a sensitive body. Localhost is exempt only when the runtime is not production.

### Deployment verification

The updater sends one request to the local Nginx listener with `Host: 130.185.75.68`. A frontend deployment fails its smoke phase unless the response is exactly HTTP 301 with the configured canonical origin as the redirect target. This verifies the complete Nginx-to-Next request path without assuming the location of the server's Nginx configuration.

## Risks / Trade-offs

- A proxy that discards the incoming Host can hide the original hostname from Next.js. The deployment smoke test detects this condition immediately.
- The middleware does not protect Django paths routed by Nginx before Next.js. Full origin lockdown remains an infrastructure task, but storefront duplication is closed by this change.
- Changing the production canonical domain requires updating `CANONICAL_SITE_URL` or `NEXT_PUBLIC_SITE_URL` and the deployment smoke variables together.

## Rollback

Revert the frontend middleware commit and the matching updater smoke check, rebuild both archives, and apply the previous release.
