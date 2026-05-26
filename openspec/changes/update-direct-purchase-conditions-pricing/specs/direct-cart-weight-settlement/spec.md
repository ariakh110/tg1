## ADDED Requirements

### Requirement: Explicit Pricing Basis

The system SHALL store and use an explicit pricing basis for each direct purchase pricing tier.

#### Scenario: Tier is priced per ton
- **WHEN** a direct order item uses a tier with `price_basis=ton`
- **THEN** the item amount is calculated as unit price times kilograms divided by 1000

#### Scenario: Tier is priced per kilogram
- **WHEN** a direct order item uses a tier with `price_basis=kg`
- **THEN** the item amount is calculated as unit price times kilograms

#### Scenario: Tier is priced per sheet
- **WHEN** a direct order item uses a tier with `price_basis=sheet` and sheet quantity
- **THEN** the item amount is calculated as unit price times sheet count

### Requirement: Controlled Purchase Conditions Before Cart

The system SHALL require users to select controlled commercial conditions before adding a direct purchase item to the cart.

#### Scenario: Buyer selects sheet dimensions and quantity
- **WHEN** a buyer starts purchase for a sheet product
- **THEN** the UI shows available pricing tiers and dimensions from the backend
- **AND** quantity and unit are selected from controlled options before the item is added to cart

#### Scenario: Buyer confirms risk terms
- **WHEN** a buyer adds the configured item to cart
- **THEN** the buyer must confirm the final-weight and settlement-difference terms
- **AND** the selected terms are preserved with the cart item and checkout metadata

### Requirement: Selected Pricing Snapshot

The system SHALL preserve the selected pricing tier, price basis, and condition label on direct store order items.

#### Scenario: Checkout creates order from cart
- **WHEN** checkout submits a cart item with `pricing_tier_id`
- **THEN** the order item references that pricing tier
- **AND** stores the selected price basis and condition label for historical display

#### Scenario: Final weight is registered
- **WHEN** an admin records final weight for a direct order item
- **THEN** the recalculated amount uses the order item's locked price basis
