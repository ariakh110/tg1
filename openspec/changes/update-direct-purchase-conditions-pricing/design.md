## Context

Kaveh Metal sells steel products whose commercial unit is not always the same as their quantity unit. A sheet can be selected by count while priced by ton, kilogram, or per sheet. Cut dimensions can also affect price. The existing `PricingTier.unit_price` has no basis, so callers implicitly treat it as price per ton.

## Goals

- Keep existing product/offer/tier model intact.
- Add enough metadata to pricing tiers to represent per-ton, per-kg, and per-sheet prices.
- Make user input controlled before cart submission.
- Keep old data compatible by defaulting existing prices to per ton.

## Non-Goals

- Full risk-rule engine.
- Inventory reservation.
- Real payment gateway integration.

## Decisions

- Decision: Add `price_basis` on `PricingTier`.
  - Reason: The same offer can legitimately have different pricing rows with different commercial basis.
  - Alternative: infer from product kind or UI unit. Rejected because it caused the current ambiguity.

- Decision: Store optional dimensions on `PricingTier` for sheet pricing conditions.
  - Reason: The price difference belongs to the commercial price row, not necessarily the canonical product spec.
  - Alternative: create a separate dimension table. Deferred until there are many reusable dimension packages.

- Decision: Keep cart client-side but require selected `pricing_tier_id`.
  - Reason: Current architecture already uses local direct cart. The backend remains source of truth when checkout is submitted.

- Decision: Save selected condition details into order item snapshots.
  - Reason: Later product/tier edits must not rewrite historical commercial terms.

## Risks

- Existing prices may have been entered as kg but will default to ton.
  - Mitigation: Admin UI exposes the basis and Excel import supports it; operators can correct rows.

- User-provided risk booklet may add more constraints later.
  - Mitigation: Selected confirmations are stored in cart metadata and order metadata so the contract can evolve.

## Migration

Existing `PricingTier` rows are migrated with `price_basis=ton` and empty dimension metadata. Existing direct order items are migrated with `price_basis=ton`.
