# Manual Deployment Tools

These files are the version-controlled source for the Kavex manual deployment workflow.

- `deploy.ps1` builds archives from committed `dev-ariakhayer` branches, validates the frontend archive, copies the canonical updater to `C:\Users\ariakh\deploy`, and optionally uploads/applies the release.
- `update.sh` is uploaded to `/opt/tirexa/update.sh` beside the release archives.
- `frontend/ops/deploy_frontend_release.sh` is carried inside `frontend.tar.gz` and performs the isolated install, build, activation, and rollback.

For manual server upload, run:

```powershell
.\ops\manual_deploy\deploy.ps1 both -PrepareOnly
```

Then upload the generated archive files and `update.sh` from `C:\Users\ariakh\deploy`. The `-PrepareOnly` option never connects to the server.

The updater migrates only the public-domain keys in the existing backend and frontend environment files. It preserves all secrets and writes a one-time `.pre-kavehmetal` backup beside each changed environment file.

For frontend releases, the updater verifies that requests carrying the public origin IP or legacy `kavex.ir` Host receive `301` to `https://kavehmetal.com`, with path and query preserved. It also verifies the lowercase ST52 redirect and the canonical sitemap directive in `robots.txt`. The defaults can be overridden with `CANONICAL_HOST`, `CANONICAL_ORIGIN`, `LEGACY_CANONICAL_HOST`, `ORIGIN_IP_HOST`, and `FRONTEND_API_URL`.
