## ADDED Requirements

### Requirement: User Direct Sales Dashboard

The system SHALL provide an authenticated user dashboard for direct Kaveh Metal purchases.

#### Scenario: User opens dashboard
- **WHEN** an authenticated user opens the account dashboard
- **THEN** the system shows direct sales summary cards
- **AND** the summary includes active orders, pending payments, overdue payments, and completed orders

#### Scenario: Marketplace requests are excluded
- **WHEN** the dashboard loads direct sales data
- **THEN** it reads direct store orders and payments
- **AND** it does not mix marketplace `OrderRequest` records into direct purchase summaries

### Requirement: User Order History And Timeline

The system SHALL let users view direct order history and order-level timelines.

#### Scenario: User lists order history
- **WHEN** a user opens the order history section
- **THEN** the system lists that user's direct store orders with status, payment status, item summary, amount, and dates

#### Scenario: User opens order detail
- **WHEN** a user opens a direct order detail page
- **THEN** the system shows locked item snapshots, destination, payment status, deadline, and status history

### Requirement: User Pending Payments

The system SHALL show pending direct payments and payment deadlines to users.

#### Scenario: Payment is pending
- **WHEN** a direct order has payment status pending or unpaid and has a payable state
- **THEN** the pending payments section shows the order, amount, due date, and payment action

#### Scenario: Payment deadline passed
- **WHEN** payment due date is in the past and the order is not paid
- **THEN** the user dashboard marks the payment as overdue
- **AND** the order remains visible until admin expires, cancels, or extends it

### Requirement: Payment Link Management

The system SHALL support payment link generation and display for direct store orders.

#### Scenario: Admin generates payment link
- **WHEN** an admin generates or refreshes a payment link for a payable direct order
- **THEN** the system stores payment link metadata on the order
- **AND** the user can see the payment link in pending payments and order detail

#### Scenario: Paid order link
- **WHEN** a direct order is already paid
- **THEN** the system does not require a new payment link
- **AND** admin is prevented from accidentally treating it as unpaid

### Requirement: Admin Direct Sales Editing

The admin dashboard SHALL allow admins to edit direct sales records and controlled operational fields.

#### Scenario: Admin edits direct order fields
- **WHEN** an admin updates contact, destination, notes, admin notes, or payment due date
- **THEN** the system saves the direct order update
- **AND** records the change in audit/status metadata where relevant

#### Scenario: Admin changes direct order status
- **WHEN** an admin changes direct order status through an allowed action
- **THEN** the system validates the transition
- **AND** writes a status history entry with actor and metadata

### Requirement: Payment Link SMS Notification

The system SHALL allow admins to send payment links by SMS and audit the result.

#### Scenario: SMS provider configured
- **WHEN** an admin sends a payment link by SMS and provider configuration is available
- **THEN** the system sends the SMS to the selected recipient
- **AND** stores a sent notification record

#### Scenario: SMS provider missing
- **WHEN** an admin sends a payment link by SMS and provider configuration is missing
- **THEN** the system does not fail silently
- **AND** stores a skipped or failed notification record with reason

### Requirement: Cart Completion

The system SHALL provide a complete cart experience for direct store checkout.

#### Scenario: User reviews cart
- **WHEN** a user opens the cart
- **THEN** the system shows cart items, quantity, price preview, and remove/update controls

#### Scenario: User continues to checkout
- **WHEN** the user proceeds from cart to checkout
- **THEN** selected cart items are carried into the direct checkout flow
