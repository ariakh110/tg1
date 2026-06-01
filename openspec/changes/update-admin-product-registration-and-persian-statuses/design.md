# Design: Admin product registration simplification and Persian labels

## Context

The existing product form exposes both common product fields and commercial pricing-condition fields at the same level. The advanced fields are still needed for per-sheet or dimension-specific pricing, but they should not block normal product creation.

## Decisions

- Keep `PricingTier.price_basis`, `condition_label`, `dimension_width_mm`, and `dimension_length_mm`.
- Move condition label and pricing dimensions into an optional advanced UI section.
- Send only cleaned numeric strings from the frontend; strip Persian digits, separators, currency/unit words, and `mm`.
- Treat unit-only optional pricing dimensions as empty on the backend.
- Keep API codes stable in English, but map all visible statuses/events to Persian in UI helpers.

## Risks

- Risk: operators may miss advanced pricing dimensions.
  - Mitigation: keep the advanced section visible as a collapsible block with a direct explanation.
- Risk: hidden optional fields may still contain old values during edit.
  - Mitigation: edit mode still loads the values; the advanced section can be opened and corrected.

## Validation

- Backend product admin-upsert test for unit-only dimension placeholders.
- Frontend lint/build.
- Manual smoke test: `/admin/dashboard` product registration and `/account/orders/{id}` history.

