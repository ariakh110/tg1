# Catalog board — spec compliance review

2026-11-06. Separate author compliance pass, not the independent code-quality review.
Binding sources: BMAD `spec-catalog-board-price-only/SPEC.md` and OpenSpec
`improve-catalog-board-price-only/specs/catalog-board/spec.md`.

| Requirement | Evidence | Result |
| --- | --- | --- |
| CAP1 factory/family/form/grade comparison | buildPriceGroups keys, numeric literal tests; nine desktop family fixtures | Pass |
| No misleading mixed units or invented facts | grouping includes price basis; tests for missing nominal/weight/date and inactive/invalid offers | Pass |
| Narrow RTL layout/actions | 390px screenshots, no page overflow, trial clicks, real reserve href; 1440px table screenshots | Pass |
| Existing filters/font/VAT/navigation | existing fetching/routing kept; IRANYekan inherited; ×0.9/×1 unchanged; post-review explicit per-table name/price ordering regression passes | Pass |
| CAP2 exact existing tier, no metadata writes | real API before/after snapshots Product/Specification/Seller/Offer/Delivery and other seller tier | Pass |
| Reject blank/bad/stale/duplicate/unknown/extra fields atomically | DB tests including injected second-save rollback; editor literal payload/browser guard | Pass |
| Permissions/no implicit create | admin-only read/write; legacy ambiguous/no-tier cases reject | Pass |
| Audit and history | native price save/signals remain in transaction; audit actor/tier/old/new recorded | Pass |
| Scope/no new schema/dependencies/live work | migration check; scoped diffs, loopback-only browser fixtures | Pass |

Plan correction: dynamic_specs was absent from public list despite plan assumption;
native read-only serializer + prefetch added and API regression verified RED→GREEN.
No approval scope changed. General file import is intentionally outside amount-only
semantics; this limitation is explicitly visible in implementation and handoff.

Post-review: stored channel/beam geometry, custom dynamic facts, precise metre
lengths and delivery/seller provenance are covered by new RED→GREEN regressions.
Admin identity now includes quantity, dimensions, negotiability and stable tier ID.
Overall: core capabilities spec-compliant locally. Admin verification timestamp
display remains a disclosed minor companion-UX omission; public date is present.
This is not a deployment, fresh post-fix browser run or real-device test.
