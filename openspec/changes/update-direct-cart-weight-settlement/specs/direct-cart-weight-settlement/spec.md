## ADDED Requirements

### Requirement: Direct Cart Before Checkout

The system SHALL add storefront product buy actions to the direct cart before direct checkout submission.

#### Scenario: Buyer clicks product buy action
- **WHEN** a buyer clicks the primary buy action on a priced storefront product
- **THEN** the product is added to the direct cart
- **AND** no direct store order is created until the buyer submits checkout for the cart

#### Scenario: Buyer submits cart checkout
- **WHEN** a buyer submits checkout from the direct cart
- **THEN** the system creates one direct store order containing the selected cart items
- **AND** marketplace `OrderRequest` records are not created

### Requirement: Controlled Quantity Units

The system SHALL support controlled quantity units for direct store items.

#### Scenario: Buyer selects ton or kilogram
- **WHEN** a buyer chooses ton or kilogram for an item
- **THEN** the backend stores the selected unit
- **AND** converts the quantity to pricing weight in kilograms and tons for price calculation

#### Scenario: Buyer selects sheet count
- **WHEN** a buyer chooses sheet count for a sheet product
- **THEN** the backend calculates estimated item weight from unit weight or sheet dimensions
- **AND** prices the item from the estimated tonnage

#### Scenario: Sheet count is invalid
- **WHEN** sheet count is selected for a non-sheet product or missing dimensions make weight impossible
- **THEN** the system rejects or marks the item as quote-required rather than silently calculating an invalid price

### Requirement: Estimated And Final Weight Settlement

The system SHALL keep estimated and final loading weights for direct store items and settle payment differences.

#### Scenario: Order is created before loading
- **WHEN** a direct store order is created
- **THEN** each priced item stores estimated weight and price weight
- **AND** the order amount is based on the estimated weight

#### Scenario: Admin registers final weight
- **WHEN** an admin records final loaded weight for order items
- **THEN** the system recalculates final item prices
- **AND** stores the total weight adjustment on the order
- **AND** writes an audit/status history event

#### Scenario: Final amount exceeds paid amount
- **WHEN** final weight increases the total order amount above paid amount
- **THEN** the order exposes a remaining amount
- **AND** the order returns to a payment-required state until the difference is settled

### Requirement: Settlement Term Fee

The system SHALL model settlement deadline and extra fee for multi-day settlement terms.

#### Scenario: Buyer chooses one-day settlement
- **WHEN** a buyer selects one-day settlement
- **THEN** the checkout applies no settlement-term fee
- **AND** the payment deadline is set from the selected term

#### Scenario: Buyer chooses multi-day settlement
- **WHEN** a buyer selects a settlement term longer than one day
- **THEN** the system adds the configured settlement-term fee to the order total
- **AND** exposes the fee separately in order details

### Requirement: Persian Direct Sales Labels

The system SHALL show Persian labels for user-facing direct sales status, events, quantity units, and settlement wording.

#### Scenario: User opens order detail
- **WHEN** a user views direct order detail or payments
- **THEN** statuses, timeline events, quantity units, and settlement amounts are shown with Persian labels
- **AND** raw backend codes are not the primary user-facing text
