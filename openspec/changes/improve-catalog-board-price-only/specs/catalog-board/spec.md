## ADDED Requirements

### Requirement: Family-aware factory price board
The product listing SHALL group by family, factory, form and grade with comparable
family-specific dimensions, numeric ordering, explicit price basis and actual
verification date, while preserving current filters, links and VAT behavior.

#### Scenario: Rebar and section comparison
- **WHEN** bars of different diameters/factories or angles/channels are listed
- **THEN** factories SHALL have distinct sections, diameters SHALL sort numerically,
  and channel nominal sizes SHALL not become fabricated heights or weights.

#### Scenario: Mobile and unknown facts
- **WHEN** the viewport is390px or facts are absent
- **THEN** the page SHALL remain usable without whole-page horizontal overflow,
  unknown facts SHALL show a dash, and actions SHALL remain keyboard/touch usable.

### Requirement: Strict existing-tier amount-only bulk pricing
Only authorized administrators SHALL list editable pricing rows and atomically
change unit_price and verification/audit/history metadata for selected existing
tiers. Product, specifications, offers, sellers, delivery, units, quantities and
conditions SHALL remain unchanged. No tier SHALL be created or deleted. This
supersedes implicit store/day-tier creation in add-bulk-price-and-vat-toggle for
the inline bulk-price panel; generic product file imports remain separate.

#### Scenario: Exact tier update
- **WHEN** an admin posts tier_id, positive valid price and matching expected_price
- **THEN** only that tier's amount and verification metadata SHALL change and other
  product/sale records SHALL remain byte-for-byte equivalent in stored fields.

#### Scenario: Bad or stale batch
- **WHEN** any row is blank/invalid, duplicated, unknown, ambiguous, stale or has extra fields
- **THEN** the whole batch SHALL fail without changes; blank SHALL NOT clear prices
  or change availability; old product_id SHALL resolve only when exactly one tier exists.
