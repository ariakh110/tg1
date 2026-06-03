## ADDED Requirements

### Requirement: Satna Receipt Approval Reversal
The system SHALL allow admins to reverse mistaken approved Satna receipt attempts without deleting the receipt or audit history.

#### Scenario: Admin reverses approved direct receipt
- **WHEN** an admin reverses an approved direct-order Satna receipt with a reason
- **THEN** the receipt SHALL be marked reversed
- **AND** the linked direct `StorePayment` SHALL no longer count as paid
- **AND** the direct order payment status SHALL be recalculated from remaining paid receipts.

#### Scenario: Admin reverses approved marketplace receipt
- **WHEN** an admin reverses an approved marketplace Satna receipt with a reason
- **THEN** the receipt SHALL be marked reversed
- **AND** marketplace operational order status SHALL not be changed automatically.

#### Scenario: Reversal requires a reason
- **WHEN** an admin attempts to reverse an approved receipt without a reason
- **THEN** the system SHALL reject the request.

#### Scenario: Reversed receipts are excluded from financial report
- **WHEN** an admin views or exports the Satna financial report
- **THEN** reversed receipts SHALL not contribute to approved receipt rows or totals.

#### Scenario: Non-admin reversal denied
- **WHEN** a non-admin user attempts to reverse an approved receipt
- **THEN** the system SHALL reject the request.
