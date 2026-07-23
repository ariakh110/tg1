## 1. Frontend Release Helper

- [x] 1.1 Add lockfile-driven dependency installation in an isolated release directory.
- [x] 1.2 Preserve production environment files before building.
- [x] 1.3 Activate the staged release only after a successful build.
- [x] 1.4 Roll back the directory and service when activation fails.

## 2. Deployment Wrapper

- [x] 2.1 Update the server updater to invoke the versioned staged-release helper.
- [x] 2.2 Validate required frontend archive entries before upload.
- [x] 2.3 Keep deployment output readable in Windows PowerShell.
- [x] 2.4 Version the manual deployment wrappers and add offline artifact preparation.

## 3. Verification And Delivery

- [x] 3.1 Test successful activation, build isolation, and restart rollback.
- [x] 3.2 Run frontend lint/build and strict OpenSpec validation.
- [x] 3.3 Commit, pull/rebase, push both repositories, and rebuild manual deployment archives.

Verification note: the production build, deployment regression tests, strict OpenSpec validation, PowerShell/Bash syntax checks, and prepare-only archive validation pass. The repository-wide standalone lint command still reports pre-existing hook-rule errors inside generated `ds-bundle` vendor files; application warnings are unchanged.

## 4. Windows Archive Line Endings

- [x] 4.1 Reproduce and confirm LF Git blob to CRLF archive conversion.
- [x] 4.2 Force LF export, add archive-byte validation, and normalize defensively on the server.
- [x] 4.3 Validate the real committed archive, synchronize GitHub, and rebuild deployment files.
