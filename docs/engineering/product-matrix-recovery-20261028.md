# Matrix submission recovery and naming — 2026-10-28

Corrective follow-up to `product-matrix-20261027` / `add-product-matrix`.

## Context and requirements

Owner reports ST52 Oxin sheets, thicknesses 8–80 mm: a connection error followed by an apparently silent attempt. Production root cause is unverified. Code inspection proves HTTP 200 invalid JSON is silently converted to an empty success response. Preview does not prominently explain invalid/all-existing results. Automatic names omit grade.

Owner explicitly requests fixing creation and both manual and automatic naming. Existing instruction delegates routine implementation decisions without repeated document approvals. This is authorization for this bounded correction, not a claim the owner reviewed these documents.

## Architecture / contract

Keep existing endpoints, admin permissions, atomic create, 100-row limit and physical identity. Optional `common.naming_mode` is `auto` (default/backward compatible) or `manual`. Optional row `name` is used only in manual mode: trimmed, nonempty, maximum 255 characters; automatic names include grade. Existing products are skipped regardless of requested name. No schema migration or external calls.

Validate successful API reports against selected row keys, status and counts; invalid JSON/HTML/malformed reports must produce visible failure. An uncertain create response must tell the owner to preview again to check existing products, never automatically repeat create. Preview must explain errors, existing-only results and the separate final registration step. Clear old reports when a request starts. Manual edits invalidate confirmation. Preserve form values on failure.

## UX

Persian RTL: naming selector above matrix, per-row name fields in manual mode, server-generated names in automatic preview, visible error/new/existing summary and pending indicator. Existing product IDs remain visible. No new design system or unrelated catalog behavior. Range syntax is not added: dimensions remain explicit comma-separated lists.

## Acceptance / verification

1. A seeded ST52/alloy/Oxin matrix with thicknesses 8 through 80 previews, creates all selected rows, then reports all existing on repeat.
2. Manual names persist exactly after trimming; blank/oversize/nontext names reject atomically; duplicate physical products remain unchanged after changing naming mode/name.
3. HTTP200 HTML, empty/malformed/wrong-key reports and network interruption cannot appear as successful zero creation. No automatic write retry.
4. Browser verifies manual/auto switching, confirmation invalidation, explicit no-create explanations and responsive RTL.
5. Run affected backend suite, frontend unit/browser tests, changed-file lint and production build; document limitations. No live deployment or live test products.
