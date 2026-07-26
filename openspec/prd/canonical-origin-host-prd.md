# PRD: Canonical origin host enforcement

## Problem

The production origin IP can be opened directly and currently returns the Next.js storefront with HTTP 200. A browser then uses a different origin, cookie jar, cache key, and client-side API context than `kavex.ir`, so users can see a fallback or stale homepage. The direct response also creates a duplicate crawlable host and bypasses the normal CDN hostname.

## Objective

All storefront navigation must converge on `https://kavex.ir`, regardless of whether the visitor enters the origin IP, `www.kavex.ir`, or another Host that reaches the server.

## Scope

- Canonical host: `kavex.ir`.
- Canonical scheme: HTTPS.
- GET and HEAD: permanent HTTP 301 redirect, preserving path and query.
- Unsafe methods: HTTP 421 on a non-canonical Host.
- Development: localhost remains available when `NODE_ENV` is not `production`.
- Deployment: an origin-IP Host smoke test runs after every frontend release.

## Acceptance Criteria

- `https://kavex.ir/` continues to return the storefront normally.
- `http://130.185.75.68/` returns `301 Location: https://kavex.ir/` after deployment.
- `http://130.185.75.68/products?family=sheet` redirects to the identical path and query on `https://kavex.ir`.
- `www.kavex.ir` and arbitrary Host values do not return storefront HTML with HTTP 200.
- A POST to a non-canonical Host is rejected and is not redirected.
- Unit tests, Next.js production build, HTTP Host probes, updater syntax checks, and strict OpenSpec validation pass.

## Deployment Note

The frontend archive and canonical `update.sh` must be uploaded together. The updater reports the observed origin-IP status and Location and exits with an error if host consolidation is not active through Nginx.
