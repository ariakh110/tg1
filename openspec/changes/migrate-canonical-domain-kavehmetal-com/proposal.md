# Change: Migrate the canonical production domain to kavehmetal.com

## Why

The new production domain is `kavehmetal.com`, but application defaults and operational tooling still publish `kavex.ir`. The domain cutover must be atomic across crawler signals, Django security settings, generated customer links, and deployment checks.

## What Changes

- Change the canonical frontend origin and all SEO policy expectations to `https://kavehmetal.com`.
- Preserve permanent host consolidation for the origin IP, `www`, legacy `kavex.ir`, and unexpected Hosts.
- Change Bale and SEO assistant defaults and migrate only persisted values containing the legacy domain.
- Make the manual updater configure public-domain environment keys with one-time backups and verify redirects plus `robots.txt` after deployment.
- Document the Cloudflare, Nginx, TLS, deploy, and verification sequence.

## Impact

- Affected specs: `technical-seo`.
- Frontend: canonical host policy, metadata environment, messaging settings UI, and SEO tests.
- Backend: messaging and SEO assistant settings plus migrations.
- Operations: manual deployment scripts and the Ubuntu/Cloudflare runbook.
