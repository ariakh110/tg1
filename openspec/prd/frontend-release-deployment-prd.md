# PRD: Reliable Frontend Release Deployment

## Summary

Kavex frontend releases must be reproducible from committed source and `package-lock.json`. A failed install, build, or service activation must not damage the version currently serving production traffic.

## Problem

The legacy updater retained production `node_modules` and built directly in the live directory. New dependencies could be missing even though they were committed, while a failed Next.js build could replace or remove live `.next` chunks and turn a feature-level build error into a site outage.

## Scope

- Build each frontend archive as a complete staged release.
- Install dependencies with `npm ci` from the committed lockfile.
- Preserve production-only environment and npm configuration files.
- Keep the active release untouched until installation and build succeed.
- Swap staged/current directories and restart the existing systemd service.
- Restore the previous release if the new service cannot become active.
- Validate archive completeness before upload.
- Keep deployment scripts in Git and support preparing files for manual upload without connecting to production.

## Out Of Scope

- Docker or Kubernetes deployment.
- CDN artifact publishing.
- Backend release isolation.
- Zero-downtime reverse-proxy traffic switching.

## Acceptance Criteria

- A dependency newly added to both package files is installed on production without a manual `npm install`.
- A failed `npm ci` or `npm run build` leaves the current source, `node_modules`, `.next`, and service untouched.
- A failed service restart restores the previous frontend directory.
- Production `.env` files are available during the staged build but remain excluded from Git archives.
- The local deployment command rejects archives missing the lockfile or release helper.
- Prepare-only mode refreshes local deployment artifacts without invoking SCP or SSH.
- Automated shell tests cover success, build failure, and restart rollback.
