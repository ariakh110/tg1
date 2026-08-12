# Change: Fix ST52 lowercase landing redirect

## Why

The ST52 landing slug was normalized from uppercase to lowercase, leaving the previously published uppercase URL as a 404. Existing links and search-engine history need a permanent one-hop migration to the canonical URL.

## What Changes

- Redirect the exact legacy ST52 path, with or without a trailing slash, to the lowercase canonical landing.
- Preserve the query string and canonical production origin.
- Verify the redirect automatically after each frontend deployment.

## Impact

- Frontend: canonical redirect policy and unit coverage.
- Deployment: frontend post-deploy smoke checks.
- SEO: legacy ST52 signals consolidate on `/category/sheet/st52` instead of ending at a 404.
