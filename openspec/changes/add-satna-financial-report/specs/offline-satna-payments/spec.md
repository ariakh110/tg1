## ADDED Requirements

### Requirement: Satna Financial Report
The system SHALL provide an admin financial report for approved Satna receipt amounts.

#### Scenario: Report totals approved receipt amounts
- **WHEN** an admin requests the Satna financial report
- **THEN** the system SHALL calculate totals from `OfflinePaymentReceipt` rows with approved status
- **AND** partial approvals SHALL contribute only their approved receipt amount.

#### Scenario: Report filters
- **WHEN** an admin filters by approval date, source type, bank account, or search text
- **THEN** the system SHALL return only matching approved receipt rows and matching aggregate totals.

#### Scenario: CSV export
- **WHEN** an admin requests the Satna financial report as CSV
- **THEN** the system SHALL return export-ready rows with receipt, payment, buyer, source, bank, reference, approval date, amount, and currency fields.

#### Scenario: Non-admin access
- **WHEN** a non-admin user requests the Satna financial report
- **THEN** the system SHALL reject the request.
