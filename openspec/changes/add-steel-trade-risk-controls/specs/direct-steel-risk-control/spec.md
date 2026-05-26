## ADDED Requirements

### Requirement: Direct orders preserve steel-market risk controls

Direct store orders SHALL store price validity, risk review status, source/market check timestamps, stock verification, proforma confirmation, and loading permission timestamps.

#### Scenario: Priced order receives price validity

- **WHEN** a priced direct store order is created
- **THEN** the order has a non-null `price_valid_until`
- **AND** the API returns `is_price_expired`
- **AND** the API returns `risk_blockers`

### Requirement: Expired prices block payment confirmation

The system SHALL reject payment confirmation for unpaid orders whose price validity has expired.

#### Scenario: Admin confirms payment after price expiry

- **GIVEN** a direct order has `price_valid_until` in the past
- **WHEN** the admin confirms payment
- **THEN** the API returns a validation error
- **AND** no paid payment is created

### Requirement: Loading is blocked until payment and risk checks pass

The system SHALL block fulfillment/loading transitions until payment is complete and required risk controls are done.

#### Scenario: Admin tries to release unpaid order

- **GIVEN** a direct order is not paid
- **WHEN** the admin transitions it to `FULFILLMENT_PENDING`
- **THEN** the API rejects the transition with a payment blocker

#### Scenario: Admin releases paid and checked order

- **GIVEN** a direct order is paid
- **AND** stock is verified
- **AND** proforma is confirmed
- **AND** risk status is not blocked
- **WHEN** the admin transitions it to `FULFILLMENT_PENDING`
- **THEN** the transition succeeds

