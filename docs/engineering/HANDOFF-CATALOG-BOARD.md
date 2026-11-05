# Catalog board and price-only editor

Task: `catalog-board-price-only`; approved inline implementation, no live actions.
Backend branch `dev-ariakhayer`, start55aecdf; frontend same branch, start65c5828.

Read `reports/catalog-board-implementation.md`, the plan
`../superpowers/plans/2026-11-05-catalog-board-price-only.md`, and the final review
report when present. Specs remain under OpenSpec `improve-catalog-board-price-only`
and BMAD `spec-catalog-board-price-only`. Query workflow status before continuing;
do not redo approved planning. Both repos contain runtime changes and need release
together; frontend-only deployment would leave the new admin API unavailable.
Release source through the existing approved workflow and rebuild with server
environment values. Do not upload this session's `.next`: verification builds
intentionally used loopback fixture API/site URLs. No environment file was edited.

The price panel now edits existing `tier_id` rows, not a product minimum or generic
upsert. Non-price fields are strictly rejected. General CSV/XLSX product editing
remains distinct and is not an amount-only tool. VAT semantics are unchanged.

All verification is isolated/local. Deployment, server/DB writes, merge/push or
provider sends have not happened. Preserve unrelated frontend handoff/purchase
inquiry documentation edits. Keep prior angle/channel seed handoff independently.

Final runtime commits: backend35fa37a, frontend e74ca20 (earlier commits in root
handoff). One independent review + one TDD pass fixed six Important findings;
511 Django/93 Node pass, touched ESLint/build pass. Earlier14 browser scenarios
pre-date the final fixes; host policy blocked additional preview, not bypassed.
No second review was claimed. See reports/catalog-board-quality-review.md and
catalog-board-final-verification.md for exact scope, evidence and two minor notes.
Next: owner chooses integration/release; staging/browser smoke before real edits.
