# PRD: Canonical domain migration to kavehmetal.com

## Problem

The production application, SEO metadata, deployment smoke tests, Bale product links, and SEO assistant context still identify `kavex.ir` as the canonical site. DNS for `kavehmetal.com` is being moved to Cloudflare and the Ubuntu origin at `130.185.75.68`. A partial cutover would create duplicate hosts, invalid callbacks, rejected Django Hosts, or metadata that points crawlers back to the old domain.

## Objective

Make `https://kavehmetal.com` the only canonical public origin while preserving every path and query when a safe request reaches the application through the origin IP, `www`, the legacy domain, or another unexpected Host.

## Scope

- Canonical origin, sitemap URLs, robots sitemap directive, Open Graph URLs, and structured-data URLs.
- Django Host, CORS, and CSRF environment configuration.
- Bale product-link base URL and SEO assistant site context, including existing rows that still contain the exact legacy domain.
- Manual deployment defaults, environment migration, backups, and post-deploy smoke tests.
- Cloudflare and Ubuntu cutover runbook.

## Non-Goals

- Parking or changing DNS for `kavex.ir` during this release.
- Migrating the existing email service or its MX, SPF, DKIM, and DMARC records.
- Automatically redirecting unrelated URLs from the historical WordPress installation without an approved URL map.

## Acceptance Criteria

- `https://kavehmetal.com` is served without a host redirect.
- Origin-IP, `www.kavehmetal.com`, `kavex.ir`, and unexpected safe Host requests return HTTP 301 to `https://kavehmetal.com` with path and query preserved.
- Canonical metadata and sitemap output contain no production reference to `kavex.ir`; `robots.txt` contains exactly one Sitemap directive for `https://kavehmetal.com/sitemap.xml`.
- Django accepts the apex and `www` domains and trusts only their HTTPS origins for browser requests.
- Existing Bale and SEO assistant settings using the old domain are migrated without overwriting unrelated custom text or secrets.
- The deploy updater creates one-time environment backups, updates only public-domain keys, runs migrations, and fails if redirect or sitemap checks regress.
- Frontend SEO tests/build, backend checks/tests, migration checks, and strict OpenSpec validation pass.

## Rollback

Cloudflare can be switched back to DNS-only or its prior records. The updater keeps `.pre-kavehmetal` copies of the two environment files, and the data migrations are reversible. Application releases can be rolled back through the existing frontend release helper and Git history.
