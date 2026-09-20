# Manual Deployment Tools

These files are the version-controlled source for the Kavex manual deployment workflow.

- `deploy.ps1` discovers the backend from its own location and the sibling `kavehmetal front` repository, builds archives from the committed `dev-ariakhayer` branches, validates the frontend archive, copies the canonical updater to the current user's `deploy` folder, and optionally uploads/applies the release as `deploy@130.185.75.68` by default.
- `update.sh` is uploaded to `/opt/tirexa/update.sh` beside the release archives.
- `frontend/ops/deploy_frontend_release.sh` is carried inside `frontend.tar.gz` and performs the isolated install, build, activation, and rollback.

The remote upload first stages files under the `deploy` user's home directory. The apply step then requests `sudo`, installs the release files under `/opt/tirexa`, and runs the updater as root. This avoids requiring direct write access to `/opt/tirexa` for the SSH account.

For manual server upload, run:

```powershell
.\ops\manual_deploy\deploy.ps1 both -PrepareOnly
```

Then upload the generated archive files and `update.sh` from `%USERPROFILE%\deploy`. The `-PrepareOnly` option never connects to the server. Use `-DeployDir` to choose another output folder and `-SshPort` for a nonstandard SSH port. Advanced overrides are available through `KAVEHMETAL_BACKEND_REPO`, `KAVEHMETAL_FRONTEND_REPO`, `KAVEHMETAL_DEPLOY_DIR`, `KAVEHMETAL_DEPLOY_SERVER`, and `KAVEHMETAL_DEPLOY_SSH_PORT`.

The updater migrates only the public-domain keys in the existing backend and frontend environment files, including the backend `FRONTEND_BASE`. It preserves all secrets and writes a one-time `.pre-kavehmetal` backup beside each changed environment file.

For frontend releases, the updater probes the local Nginx HTTPS listener and verifies that requests carrying the public origin IP or legacy `kavex.ir` Host receive `301` to `https://kavehmetal.com`, with path and query preserved. It also verifies the lowercase ST52 redirect and requires exactly one canonical sitemap directive in `robots.txt`. A valid Nginx TLS listener must therefore be configured before applying this domain-migration release. The defaults can be overridden with `CANONICAL_HOST`, `CANONICAL_ORIGIN`, `LEGACY_CANONICAL_HOST`, `ORIGIN_IP_HOST`, and `FRONTEND_API_URL`.
