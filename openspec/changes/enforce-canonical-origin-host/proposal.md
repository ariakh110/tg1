# Change: Enforce the canonical production host

## Why

The public origin IP and arbitrary Host headers currently return the storefront with HTTP 200. This creates a duplicate origin, separates browser cookies and client-side API state, bypasses the CDN hostname, and can expose a visually different homepage even though the deployed build is identical.

## What Changes

- Add a production request guard that permanently redirects safe requests from the origin IP, `www`, the legacy domain, and any unexpected Host to the configured canonical origin (currently `https://kavehmetal.com`).
- Preserve the requested path and query string during host consolidation.
- Reject non-idempotent requests sent to an unexpected Host instead of forwarding their body through a redirect.
- Add automated policy tests and a post-deploy smoke test for the origin-IP redirect.

## Impact

- Frontend: root middleware and canonical-host policy tests.
- Deployment: `ops/manual_deploy/update.sh` verifies the redirect through the local Nginx listener after a frontend release.
- SEO/security: a single public origin is exposed for storefront pages while direct development access remains available outside production.
