## ADDED Requirements

### Requirement: Direct Store Orders Are Separate From Marketplace Requests

The system SHALL represent direct Kaveh Metal product purchases separately from marketplace buy/sell request records.

#### Scenario: Buyer submits direct product order
- **WHEN** a buyer submits a checkout for a Kaveh catalog product
- **THEN** the system creates a direct store order
- **AND** it does not create a marketplace `OrderRequest`

#### Scenario: Marketplace requests remain unchanged
- **WHEN** a verified user publishes a buy or sell announcement in the marketplace
- **THEN** the system continues to use the existing marketplace request workflow
- **AND** the direct store order list is not polluted with that announcement

### Requirement: Product CTAs Route To Direct Store Flows

The storefront SHALL route direct product purchase actions to cart, checkout, quote, or backorder flows instead of the marketplace request board.

#### Scenario: Priced product CTA
- **WHEN** a product has an active offer with a valid price
- **THEN** the product list and detail primary action routes the buyer to a direct buy/cart/checkout flow
- **AND** the CTA does not point to `/orders`

#### Scenario: Price-less product CTA
- **WHEN** a product is active but has no valid price
- **THEN** the primary action routes the buyer to a direct quote request flow
- **AND** the CTA does not point to `/orders`

#### Scenario: Out-of-stock product CTA
- **WHEN** a product is out of stock
- **THEN** the primary action routes the buyer to a direct backorder/store request flow
- **AND** the CTA does not point to `/orders`

### Requirement: Checkout Locks Item Snapshots

The system SHALL lock item-level product, price, specification, and delivery data when a direct store order is submitted.

#### Scenario: Catalog changes after checkout
- **WHEN** a product price, title, specification, or delivery origin changes after checkout submission
- **THEN** the existing direct store order item keeps its original locked snapshot
- **AND** admin and buyer order history show the locked checkout values

### Requirement: Quote Orders Handle Products Without Price

The system SHALL support direct quote orders for products that are available but do not have a valid current price.

#### Scenario: Buyer requests quote
- **WHEN** a buyer submits a direct request for a product without a valid price
- **THEN** the system creates a direct store order in quote status
- **AND** admin can review and confirm a price before payment is requested

### Requirement: Admin Direct Sales Management

The admin dashboard SHALL expose direct sales orders separately from KYC and marketplace order requests.

#### Scenario: Admin lists direct sales
- **WHEN** an admin opens the direct sales section
- **THEN** the system lists direct store orders with buyer, status, amount, item summary, and timestamps
- **AND** it does not require loading marketplace order request data

#### Scenario: Admin changes order status
- **WHEN** an admin transitions a direct store order status
- **THEN** the system validates the transition
- **AND** writes a status history entry with actor and metadata

### Requirement: Payment State Is Gateway-Ready

The system SHALL model payment status for direct orders in a way that can support manual confirmation first and gateway callbacks later.

#### Scenario: Manual payment confirmation
- **WHEN** an admin confirms payment manually
- **THEN** the order payment status becomes paid
- **AND** the order status history records the event

#### Scenario: Future gateway callback
- **WHEN** a payment gateway callback is received in a later implementation
- **THEN** the payment reference can be processed idempotently without creating duplicate payments
