## 1. Application migration

- [x] 1.1 Change frontend canonical defaults, admin placeholders, and SEO policy tests to `kavehmetal.com`.
- [x] 1.2 Change Bale and SEO assistant defaults and add conservative data migrations.
- [x] 1.3 Update the active SEO strategy domain without rewriting historical migration files.

## 2. Deployment and operations

- [x] 2.1 Update manual deploy defaults and final status output.
- [x] 2.2 Upsert public-domain environment keys with one-time backups while preserving secrets.
- [x] 2.3 Add smoke assertions for the origin IP, legacy Host, lowercase ST52 URL, and canonical sitemap directive.
- [x] 2.4 Document the Cloudflare, Nginx, TLS, deploy, and rollback procedure.

## 3. Verification and delivery

- [x] 3.1 Run frontend SEO tests, lint, and production build.
- [x] 3.2 Run Django checks, migrations check, focused tests, and migration tests.
- [x] 3.3 Run shell syntax, strict OpenSpec, and diff validation.
- [ ] 3.4 Commit and push both repositories, then rebuild the manual deployment files.
- [ ] 3.5 After production cutover, verify live redirects, canonical tags, sitemap, robots, API, admin, and webhook URLs.

## Verification Notes

- Frontend: 19 SEO tests passed; lint and production build passed. Six pre-existing lint warnings remain outside this change.
- Backend: Django check, migration drift check, and all 58 focused messaging/SEO assistant tests passed.
- Full backend suite: 263 of 265 tests passed. Two existing `sales.tests.LoadingVehicleWeighbridgeTests` error because their fixture still supplies removed `StoreOrderItem.unit_price` and `total_price` arguments; this migration does not touch that workflow.
- Operations: Bash and PowerShell syntax checks, local production Host probes, diff checks, and all affected strict OpenSpec validations passed.
