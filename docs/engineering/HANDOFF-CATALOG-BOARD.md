# Catalog board and price-only editor

Task: `catalog-board-price-only`; approved inline implementation, no live actions.
Backend branch `dev-ariakhayer`, start55aecdf; frontend same branch, start65c5828.

Read `reports/catalog-board-implementation.md`, the plan
`../superpowers/plans/2026-11-05-catalog-board-price-only.md`, and the final review
report when present. Specs remain under OpenSpec `improve-catalog-board-price-only`
and BMAD `spec-catalog-board-price-only`. Query workflow status before continuing;
do not redo approved planning. Both repos contain runtime changes and need release
together; frontend-only deployment would leave the new admin API unavailable.

The price panel now edits existing `tier_id` rows, not a product minimum or generic
upsert. Non-price fields are strictly rejected. General CSV/XLSX product editing
remains distinct and is not an amount-only tool. VAT semantics are unchanged.

All verification is isolated/local. Deployment, server/DB writes, merge/push or
provider sends have not happened. Preserve unrelated frontend handoff/purchase
inquiry documentation edits. Keep prior angle/channel seed handoff independently.

Next: final independent review/fix verification, then owner chooses integration.
