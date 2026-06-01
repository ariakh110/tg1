## ADDED Requirements

### Requirement: Persian Direct Sales Labels

The system SHALL show Persian labels for all user-facing direct sales status, events, quantity units, settlement wording, and admin direct-sales filters.

#### Scenario: User opens order detail history
- **WHEN** a user views direct order detail or payments
- **THEN** statuses, timeline events, quantity units, and settlement amounts are shown with Persian labels
- **AND** raw backend event codes such as `STORE_ORDER_SHIPPED` and `STORE_ORDER_COMPLETED` are not shown as the primary text.

#### Scenario: Admin filters direct sales orders
- **WHEN** an admin opens direct-sales filters
- **THEN** status and payment-status options are displayed with Persian labels
- **AND** the submitted filter values remain stable backend codes.
