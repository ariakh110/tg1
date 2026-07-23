## Context

Frontend source archives intentionally exclude `node_modules`, `.next`, and production environment files. The previous updater copied source over the active directory while retaining those runtime directories. This was fast but made dependency state differ from `package-lock.json` and allowed a failed build to damage the files used by the running service.

## Goals / Non-Goals

- Goals: deterministic dependency installation, isolated builds, short activation time, automatic rollback, and preservation of production configuration.
- Goals: keep the existing manual archive and systemd deployment model.
- Non-Goals: introduce containers, a remote artifact registry, blue-green proxy routing, or change backend deployment in this change.

## Decisions

### Build a complete staged release

The updater extracts `frontend.tar.gz` to `/opt/tirexa/frontend_release`. A versioned helper from that archive copies supported environment files from the current release, runs `npm ci --no-audit --no-fund`, and runs the production build inside staging.

`npm ci` is intentionally used instead of reusing or incrementally updating `node_modules`: production receives exactly the dependency graph represented by the committed lockfile, including newly added Editor.js tools.

### Swap only after successful build

The current directory is renamed to a temporary previous-release path only after install and build both succeed. The staged directory is then renamed to the stable frontend path and systemd is restarted. Directory renames occur on the same filesystem, so activation is short and the active build is never partially overwritten.

### Roll back service activation failure

An exit trap restores the previous directory and restarts the old service when restart or active-state verification fails. After a successful restart, the previous release is removed.

### Keep production configuration outside source control

The helper copies `.env`, environment-specific variants, and `.npmrc` from the current release before installation and build. These files remain absent from the Git archive.

### Reject incomplete archives locally

The PowerShell deployment wrapper checks that `package.json`, `package-lock.json`, and `ops/deploy_frontend_release.sh` are present before upload. This prevents an old or incomplete branch archive from reaching the server.

## Risks / Trade-offs

- `npm ci` makes frontend deployment slower and requires npm registry access. This is accepted in exchange for deterministic production dependencies; the server npm cache still reduces repeated download cost.
- A staged release temporarily consumes disk for a second source tree, dependencies, and build. The updater removes the previous release after successful activation.
- Directory rollback cannot repair an unrelated systemd or host failure, but it guarantees that a release-specific startup failure restores the last source/build tree.

## Migration Plan

1. Commit and archive the deployment helper with the frontend.
2. Upload the new `frontend.tar.gz` and external `update.sh`.
3. Run `bash /opt/tirexa/update.sh frontend`.
4. The first corrected release installs all locked dependencies and replaces the currently broken frontend only after a successful build.

Rollback is automatic on activation failure. Before activation, any install or build failure leaves `/opt/tirexa/frontend` unchanged.

## Open Questions

- None.
