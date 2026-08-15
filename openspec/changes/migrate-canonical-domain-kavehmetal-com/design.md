## Context

`kavehmetal.com` is managed in Cloudflare and the application origin is the Ubuntu VPS at `130.185.75.68`. The project already enforces one canonical Host in Next.js middleware, so the migration changes configuration and persisted public URLs rather than introducing another redirect layer.

## Goals / Non-Goals

- Goals: one canonical HTTPS origin, consistent crawler signals, safe Django browser origins, current Bale links, repeatable manual deployment, and a reversible cutover.
- Non-goals: old-domain DNS parking, mail migration, or speculative redirects for historical WordPress paths.

## Decisions

- Use the apex `https://kavehmetal.com` as the canonical origin. `www` is accepted at DNS/TLS but permanently consolidated to the apex by the existing middleware.
- Keep Host consolidation in application middleware so path/query preservation and unsafe-method rejection remain identical for the IP, old domain, and arbitrary Hosts.
- Run Cloudflare records as DNS-only until Nginx serves the new Host and Let's Encrypt has issued a valid certificate. Enable the proxy only after HTTPS works directly.
- Let `update.sh` upsert only six public-domain environment keys. Existing secrets are untouched and each environment file receives a one-time `.pre-kavehmetal` backup.
- Run post-deploy probes against the local Nginx HTTPS listener with explicit local address overrides. This validates the certificate-enabled virtual-host path without depending on Cloudflare and remains correct when Nginx redirects port 80 to HTTPS.
- Migrate persisted application data conservatively: exact legacy Bale base URLs and occurrences of `kavex.ir` in the singleton SEO context are replaced; other custom values remain unchanged.

## Risks / Trade-offs

- Enabling the Cloudflare proxy before origin TLS is valid can hide certificate or virtual-host errors. Mitigation: complete DNS-only and direct-origin checks first.
- A stale systemd environment can reject the new Host. Mitigation: updater writes the existing environment files before restart and smoke tests the public Host locally.
- The old domain will not redirect publicly until its DNS is pointed at this stack. The code is ready for that later cutover, but this release intentionally does not change old-domain DNS.

## Migration Plan

1. Point only `@` and `www` for `kavehmetal.com` to the VPS in Cloudflare with proxy disabled.
2. Add the new names to the active Nginx virtual host without changing existing certificate paths, then issue a certificate with Certbot.
3. Upload the committed backend/frontend archives and updater, then run `bash /opt/tirexa/update.sh both`.
4. Verify HTTPS, canonical metadata, sitemap, robots, API, admin login, and Bale webhook configuration.
5. Set Cloudflare SSL/TLS to Full (strict), enable the proxy, and then enable Always Use HTTPS.
6. Keep email DNS records unchanged until mail migration is separately planned.

## Rollback

Disable the Cloudflare proxy, restore the previous DNS record if required, restore `.env.pre-kavehmetal` and `.env.production.local.pre-kavehmetal`, and deploy the prior Git revisions. Reverse Django migrations only if application code is also rolled back.
