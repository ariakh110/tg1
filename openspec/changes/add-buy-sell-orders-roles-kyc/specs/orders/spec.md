## ADDED Requirements

### Requirement: Create BUY and SELL orders
The system SHALL allow authenticated users to create BUY and SELL orders with typed fields and timestamps.

#### Scenario: Buyer creates a BUY order
- **WHEN** an authenticated user submits a BUY order payload
- **THEN** the system creates an Order with type=BUY and status=OPEN

#### Scenario: Seller creates a SELL order
- **WHEN** an authenticated seller submits a SELL order payload
- **THEN** the system creates an Order with type=SELL and status=OPEN

### Requirement: Submit offers on orders
The system SHALL allow offers to be submitted against OPEN orders, with visibility restricted to the order owner.

#### Scenario: Seller submits offer for BUY order
- **WHEN** a seller submits an offer on a BUY order
- **THEN** the offer is created and visible to the BUY order owner only

#### Scenario: Buyer submits offer for SELL order
- **WHEN** a buyer submits an offer on a SELL order
- **THEN** the offer is created and visible to the SELL order owner only

### Requirement: Accept offers and transition status
The system SHALL allow the order owner to accept one offer and decline other offers, moving the order to the next state.

#### Scenario: Accept offer on BUY order
- **WHEN** the BUY order owner accepts an offer
- **THEN** the order status changes to OFFER_SELECTED and other offers are declined

#### Scenario: Accept offer on SELL order
- **WHEN** the SELL order owner accepts an offer
- **THEN** the order status changes to OFFER_SELECTED and other offers are declined

### Requirement: State transitions are validated
The system SHALL enforce allowed status transitions for BUY/SELL orders via a centralized service.

#### Scenario: Invalid transition is rejected
- **WHEN** a transition is requested that is not allowed for the order type/status
- **THEN** the system returns a conflict error and does not change the order

### Requirement: Order access is restricted to participants
The system SHALL restrict order detail access to the order owner, the accepted counterparty, and admins.

#### Scenario: Non-participant access is denied
- **WHEN** a user who is not a participant requests order details
- **THEN** the system returns a forbidden response

### Requirement: API versioning for orders and offers
The system SHALL expose order and offer endpoints under `/api/v1` without altering existing `/api` endpoints.

#### Scenario: Create order via v1
- **WHEN** a client calls `/api/v1/orders`
- **THEN** the order is created per the v1 contract
