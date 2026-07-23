# Change: Harden frontend release deployment

## Why

The production updater reused the live `node_modules` directory and ran `next build` directly inside the active frontend tree. A release that added `@editorjs/table` therefore failed with `Module not found`, and the failed build also left the live `.next` output inconsistent enough to crash `/admin/content`.

## What Changes

- Install the exact dependency graph from `package-lock.json` for every frontend release.
- Extract, install, and build in a staging directory without modifying the active release.
- Preserve production environment and npm configuration files in the staged release.
- Activate a release only after a successful install and build.
- Restore the previous release automatically if the frontend service cannot restart or become active.
- Validate that the frontend archive contains its manifest, lockfile, and deployment helper before upload.

## Impact

- Affected spec: `frontend-release-deployment`
- Affected frontend: new versioned release helper and deployment regression test
- Affected deployment tooling: `C:\Users\ariakh\deploy\update.sh` and `deploy.ps1`
- Database migrations: none
