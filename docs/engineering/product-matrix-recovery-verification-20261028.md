# Matrix recovery: implementation and verification

Follow-up spec: product-matrix-recovery-20261028.md; OpenSpec fix-product-matrix-recovery. Author: Codex, 2026-10-28.

## Implementation

Backend optional common.naming_mode auto/manual; per-row name in manual mode (trimmed, required, <=255). Automatic names include grade, existing identities remain create-only and unchanged. Frontend strict report boundary validates successful and error reports; malformed responses cannot create false success or crash rows rendering. Preview summaries explain new/all-existing/error states; uncertain create guidance always asks for fresh preview. Form values preserved, confirmation cleared, no automatic create retry. Naming mode switch supports editing auto-preview names manually.

## Spec review

Acceptance met locally: 73 individual thicknesses 8–80 and a separate 34-row ST52 Oxin case at width2000/lengths6000,12000. Both persist distinct products. Manual names persist, invalid names reject entire batch, repeats preserve names/prices/stock. Preview read-only and products permissions retain prior tests. Existing API default remains auto. 146 rows remain intentionally rejected by the 100-row limit. Exact production incident cause unverified; no server logs or live writes used.

## Quality / independent review

Fresh read-only reviewer `matrix_recovery_review` reviewed both repositories; no Critical issue, two Important issues found. Both accepted and fixed together: malformed non-2xx rows could crash rendering; JSON detail on gateway failure omitted reconciliation suffix. Regression test failed on forwarding malformed report, then passed after validating reports and appending suffix outside message choice. Entire frontend unit suite and production browser rerun passed after fixes. No minor findings deferred. Reviewer did not re-review the fix pass.

## Commands and results

- Backend `.venv/Scripts/python.exe manage.py test products accounts.test_admin_sections --settings=tg1.settings_test --noinput`: 131 passed, 19.577s. Mocked late write exception printed intentionally; test passes proving rollback.
- Backend `manage.py check` and `makemigrations --check --dry-run --settings=tg1.settings_test`: clean, no changes.
- Frontend `node --test tests/*.test.mjs`: 60 passed. New naming/missing-module tests first RED, then GREEN. Review regression RED then GREEN.
- Changed frontend files `npx.cmd eslint ...`: exit0. Unchanged AdminDashboardPage legacy lint baseline outside scope; no full-repository lint claim.
- `npm.cmd run build`: exit0 after final transport fixes; existing middleware deprecation warning remains unrelated.
- Production server localhost:3000 + `tests/productMatrix.browser.cjs`: 12 mocked previews, 2 mocked create attempts (one success, one gateway failure), no page errors or unexpected writes. Manual/auto names, stale confirmation, HTML/empty/bad error reports, uncertain result recovery and existing-only summaries verified. Desktop/mobile screenshots inspected.
- `git diff --check`: no whitespace errors. OpenSpec CLI absent from PATH; delta files reviewed manually, no CLI validation claim.

Evidence: Windows TEMP `matrix-recovery-{backend,node-final,build-final,browser-final}.log`; screenshots/checks `kavehmetal-matrix-recovery-production/`. Provider calls and all browser API writes mocked. Backend uses isolated test DB. Production DB, logs, PostgreSQL races and internet/proxy connectivity not validated.

## Execution rulings

Retain existing non-main checkouts and scoped staging to preserve canonical workflow DB, dependencies and unrelated frontend docs. Cost: unscoped staging would mix unrelated edits; explicitly excluded. Dimensions remain explicit comma lists, not range syntax; this preserves agreed 100-row boundary. No deployment authorized by this correction; prepare archives only under standing release preparation authorization.
