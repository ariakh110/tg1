# Manual Deployment Tools

These files are the version-controlled source for the Kavex manual deployment workflow.

- `deploy.ps1` discovers the backend from its own location and the sibling `kavehmetal front` repository, builds archives from the committed `dev-ariakhayer` branches, validates the frontend archive, copies the canonical updater to the current user's `deploy` folder, and optionally uploads/applies the release as `deploy@130.185.75.68` by default.
- `update.sh` is uploaded to `/srv/tirexa/update.sh` beside the release archives.
- `frontend/ops/deploy_frontend_release.sh` is carried inside `frontend.tar.gz` and performs the isolated install, build, activation, and rollback.

The remote upload first stages files under the `deploy` user's home directory. The apply step then requests `sudo`, installs the release files under `/srv/tirexa`, and runs the updater as root. This avoids requiring direct write access to `/srv/tirexa` for the SSH account.

For backend releases, the updater discovers the Python environment used by the systemd service or a conventional `/srv/tirexa` virtual-environment path. It creates `.venv` only when no existing environment is available, synchronizes `requirements.txt`, and then runs migrations and `collectstatic`.

After migrations, `update.sh` runs the idempotent catalog baseline and market synchronization commands. IME synchronization reads the official physical-trade service with a bounded request and keeps the last successful rows if that service is unavailable. Global synchronization is skipped with a warning until a provider key is configured. The post-deploy checks request all three market APIs and both new pages.

The updater restarts any installed `tirexa-celery`, `tirexa-celery-worker`, or `tirexa-celery-beat` systemd units so the daily schedules load the new tasks. If no beat unit is installed, run the two sync management commands from cron or add a Celery beat service before relying on unattended updates.

Optional global-market configuration belongs only in `/srv/tirexa/backend/.env`:

```dotenv
METALS_DEV_API_KEY=replace-with-server-side-key
MARKET_HTTP_TIMEOUT_SECONDS=15
GLOBAL_METALS_MIN_REFRESH_HOURS=20
```

Do not add `METALS_DEV_API_KEY` to any `NEXT_PUBLIC_*` frontend variable. Without it, `/global-metals` displays a clear unavailable state and any reviewed CSV observations remain visible. Staff can upload CSV to `POST /api/admin/global-metals/import/` using the authenticated admin token, or run `python manage.py import_global_metals /path/to/file.csv`. Required headers are `instrument_code,name_fa,name_en,price,currency,unit,exchange,observed_at,provider,source_url`.

For manual server upload, run:

```powershell
.\ops\manual_deploy\deploy.ps1 both -PrepareOnly
```

Then upload the generated archive files and `update.sh` from `%USERPROFILE%\deploy`. The `-PrepareOnly` option never connects to the server. Use `-DeployDir` to choose another output folder and `-SshPort` for a nonstandard SSH port. Advanced overrides are available through `KAVEHMETAL_BACKEND_REPO`, `KAVEHMETAL_FRONTEND_REPO`, `KAVEHMETAL_DEPLOY_DIR`, `KAVEHMETAL_DEPLOY_SERVER`, `KAVEHMETAL_DEPLOY_SSH_PORT`, and `KAVEHMETAL_APP_ROOT`.

The updater migrates only the public-domain keys in the existing backend and frontend environment files, including the backend `FRONTEND_BASE`. It preserves all secrets and writes a one-time `.pre-kavehmetal` backup beside each changed environment file.

For frontend releases, the updater probes the local Nginx HTTPS listener and verifies that requests carrying the public origin IP or legacy `kavex.ir` Host receive `301` to `https://kavehmetal.com`, with path and query preserved. It also verifies the lowercase ST52 redirect and requires exactly one canonical sitemap directive in `robots.txt`. A valid Nginx TLS listener must therefore be configured before applying this domain-migration release. The defaults can be overridden with `CANONICAL_HOST`, `CANONICAL_ORIGIN`, `LEGACY_CANONICAL_HOST`, `ORIGIN_IP_HOST`, and `FRONTEND_API_URL`.
