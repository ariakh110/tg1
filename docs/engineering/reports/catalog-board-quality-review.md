# Catalog board — independent quality review and single fix pass

2026-11-06. Independent reviewer: fresh-context `gpt-6-astra`, xhigh; read-only,
no delegation. Backend55aecdf..1ee3b9e, frontend65c5828..15b2225. The reviewer
read both code ranges, binding spec/plan/ledger and supplied evidence; independently
ran9 focused Node tests and reproduced presentation defects. Verdict before fixes:
**With fixes**. No Critical issue found. Exact-tier atomic write boundary was sound.

## Findings, severity calibration and disposition

1. **Important: indistinguishable admin conditions** (`BulkPricePanel.js`,
   `products/price_updates.py`). Expose tier width/length/negotiability; show stable
   tier ID, quantity bounds and dimension conditions in visible and accessible
   descriptions. Real API twin-tier regression and pure description regression.
2. **Important: explicit sorting ignored** (`productBoard.mjs`, client). Pass selected
   ordering into grouping; sort name/ascending/descending amount inside comparable
   factory/basis tables, dimensions only by default. Labels say “در هر جدول”, so
   unrelated units are never ranked by raw amount. Literal default/three-options test.
3. **Important: metre precision drift** (`productBoard.mjs`). Dedicated metre formatter
   retains five decimals supported by millimetre model precision. Tests12005mm and
   12005.01mm; neither becomes a different cut length.
4. **Important: stored channel/beam geometry omitted** (`productBoard.mjs`, component).
   Add actual stored channel height and beam width/thickness columns conditionally
   using group products. Nominal channel size never generates an inferred height.
5. **Important: delivery/seller provenance lost** (`productBoard.mjs`). Restore native
   warehouse/factory address labels; independently fall back to active seller even
   without delivery rows. Test native place codes and missing-delivery seller.
6. **Reviewer Minor → executor Important: custom dynamic attributes hidden**.
   Reason: a valid custom family may have only these facts; empty common numeric
   columns make the all-family fallback ineffective. Preserve literal stored
   name/value/unit in supplemental desktop/mobile facts. Unit regression covers
   arbitrary text and precision, without fabricated conversion.

All six entered **one TDD fix pass**, no second reviewer. The six frontend regressions
failed on the old code (9pass/6fail), then all15 focused tests passed after fixes.
The real API dimension-condition regression failed with missing key before the
service output correction. Full post-fix results are in final-verification report.

## Deferred minors (exhaustive)

- Admin `price_verified_at` is available from API but not displayed in editor;
  public board still displays actual tier verification date.
- Existing global floating inquiry trigger may cover a product label at some
  scroll positions. Separate action trial clicks passed; scrolling remains possible.
  This component was not redesigned in this change.

## Declined-to-judge rulings (exhaustive)

- Generic CSV/XLSX mutations: reaffirm separate, explicitly approved product-editing
  workflow; the strict price-panel promise does not apply to generic import.
  Cost: importing supplied metadata there can still edit those fields.
- VAT policy correctness: retain approved off×0.9/on×1, not an accounting-policy
  reassessment. Cost: any pre-existing policy discrepancy remains.
- General permissions/detail/buy pricing: no broad redesign. New editor gate was
  inspected. Cost: unrelated pre-existing policy issues are not cured here.

Author disposition: no known unresolved Important/Critical from this review.
This statement rests on regressions and final suite, not on a second review.
