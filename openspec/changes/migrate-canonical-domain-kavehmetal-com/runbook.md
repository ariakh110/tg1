# Production Cutover Runbook

## Preconditions

- Cloudflare `A @` points to `130.185.75.68` with proxy disabled.
- Cloudflare `CNAME www` points to `kavehmetal.com` with proxy disabled.
- Registrar nameservers match the two nameservers shown in the Cloudflare Overview page.
- Existing mail records are left unchanged.

## Ubuntu sequence

1. Connect and inspect the active Nginx virtual host:

   ```bash
   ssh root@130.185.75.68
   sudo nginx -T 2>/dev/null | grep -n -B 2 -A 8 'server_name'
   ```

2. Edit the matching file under `/etc/nginx/sites-available/`. Add `kavehmetal.com www.kavehmetal.com` to the existing `server_name` line. Do not change the existing certificate paths by hand. Then validate and reload:

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. Issue the new certificate while Cloudflare is still DNS-only:

   ```bash
   sudo apt update
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d kavehmetal.com -d www.kavehmetal.com --redirect
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. Upload `backend.tar.gz`, `frontend.tar.gz`, and `update.sh` to `/opt/tirexa/`, then apply the release:

   ```bash
   bash /opt/tirexa/update.sh both
   ```

5. Inspect the configured public-domain keys without displaying secrets:

   ```bash
   grep -E '^(DJANGO_ALLOWED_HOSTS|CORS_ALLOWED_ORIGINS|CSRF_TRUSTED_ORIGINS|FRONTEND_BASE)=' /opt/tirexa/backend/.env
   grep -E '^(NEXT_PUBLIC_SITE_URL|CANONICAL_SITE_URL|NEXT_PUBLIC_API_URL)=' /opt/tirexa/frontend/.env.production.local
   ```

6. Verify the origin before enabling the Cloudflare proxy:

   ```bash
   curl -I https://kavehmetal.com/
   curl -I https://www.kavehmetal.com/products?family=sheet
   curl -s https://kavehmetal.com/robots.txt
   curl -I https://kavehmetal.com/sitemap.xml
   curl -I https://kavehmetal.com/api/site-settings/
   ```

   The robots output must contain exactly this one Sitemap directive and no `kavex.ir` reference:

   ```text
   Sitemap: https://kavehmetal.com/sitemap.xml
   ```

## Cloudflare completion

1. Set SSL/TLS encryption mode to Full (strict).
2. Turn the `@` and `www` records to Proxied.
3. Enable Always Use HTTPS.
4. Do not cache `/api/*`, `/admin/*`, `/django-admin/*`, `/auth/*`, or `/account/*`.
5. Re-run the public verification commands and verify canonical links in page source.

## Application follow-up

- In the admin messaging settings, confirm Site Base URL is `https://kavehmetal.com`.
- Re-register the Bale webhook so its URL uses the new domain.
- In the Kavenegar developer panel, replace any configured delivery-status and incoming-message callbacks with `https://kavehmetal.com/api/messaging/kavenegar/status/<secret>/` and `https://kavehmetal.com/api/messaging/kavenegar/incoming/<secret>/`.
- Update allowed origins or callback URLs in any enabled OAuth or payment provider before testing those flows.
- Add `https://kavehmetal.com/sitemap.xml` as a new property/sitemap in Search Console.
- Do not request indexing for account, authentication, checkout, buy-intent, or API URLs.
