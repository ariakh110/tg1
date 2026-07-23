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
