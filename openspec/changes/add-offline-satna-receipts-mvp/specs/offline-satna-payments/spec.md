## ADDED Requirements

### Requirement: Satna Payment Sources
The system SHALL allow authenticated buyers to initiate Satna receipt payments for payable direct store orders and accepted marketplace trades.

#### Scenario: Satna amount is eligible
- **WHEN** a buyer initiates Satna payment for an amount of at least 1,000,000,000 toman
- **THEN** the system SHALL allow Satna initiation without applying a software upper limit.

#### Scenario: Satna amount is below the minimum
- **WHEN** a buyer initiates Satna payment for an amount below 1,000,000,000 toman
- **THEN** the system SHALL reject the request with a Persian minimum-amount message.

#### Scenario: Direct buyer selects Satna
- **WHEN** a buyer submits a payable direct checkout with Satna selected
- **THEN** the system SHALL create an active offline payment for the direct order remaining amount.

#### Scenario: Marketplace buyer initiates Satna
- **WHEN** a marketplace offer has been accepted and the buyer initiates Satna payment
- **THEN** the system SHALL create an active offline payment for the full agreed amount.

#### Scenario: Listing is not a payment source
- **WHEN** a user attempts to initiate payment for an `OrderRequest`
- **THEN** the system SHALL reject the request.

### Requirement: Satna Deadline And Bank Details
The system SHALL assign the configured primary bank account and calculate Satna deadlines at 10:00 Asia/Tehran.

#### Scenario: Admin adds destination accounts
- **WHEN** an admin adds one or more valid Satna destination accounts
- **THEN** the system SHALL persist the account number, IBAN, bank name, and account holder and SHALL make the first active account primary automatically.

#### Scenario: Admin changes the primary account
- **WHEN** an admin selects another active destination account as primary
- **THEN** new Satna payments SHALL use that account while existing payments retain their snapshotted destination details.

#### Scenario: Direct deadline
- **WHEN** a direct Satna payment is created
- **THEN** its deadline SHALL be 10:00 Asia/Tehran on the selected settlement-term due date.

#### Scenario: Marketplace deadline
- **WHEN** a marketplace Satna payment is created
- **THEN** its deadline SHALL be 10:00 Asia/Tehran on the next day.

### Requirement: Receipt Upload Validation
The system SHALL accept controlled Satna receipt uploads and preserve each attempt.

#### Scenario: Buyer uploads a valid receipt
- **WHEN** the payment owner uploads a valid JPG, JPEG, PNG, or PDF up to 5MB with a numeric reference number
- **THEN** the system SHALL store the attempt and mark the payment pending review.

#### Scenario: Buyer exceeds upload limit
- **WHEN** a buyer attempts more than five receipt uploads in one hour
- **THEN** the system SHALL reject the upload.

### Requirement: Admin Receipt Review
The system SHALL let admins approve, reject, and unlock Satna payments with an audit trail.

#### Scenario: Direct receipt approved
- **WHEN** an admin approves a direct-order Satna receipt
- **THEN** the system SHALL create an idempotent paid `StorePayment` record and update direct settlement state.

#### Scenario: Marketplace receipt approved
- **WHEN** an admin approves a marketplace Satna receipt
- **THEN** the system SHALL record the approved payment without automatically changing marketplace operational order status.

#### Scenario: Third rejection
- **WHEN** an admin rejects the third receipt attempt
- **THEN** the system SHALL lock further receipt uploads until an admin unlocks the payment.

### Requirement: Protected Receipts And Email Logs
The system SHALL protect receipt-file access and log transactional email delivery.

#### Scenario: Deadline reminder
- **WHEN** an active Satna payment reaches the two-hour reminder window
- **THEN** the periodic worker SHALL send and log one reminder email.

#### Scenario: Deadline expires
- **WHEN** an active unlocked Satna payment passes its deadline
- **THEN** the periodic worker SHALL mark it expired and SHALL send and log one expiration email.

#### Scenario: Receipt file access
- **WHEN** a receipt owner or admin requests the current receipt file
- **THEN** the system SHALL stream the file through an authenticated endpoint.

#### Scenario: SMTP failure
- **WHEN** transactional email delivery fails
- **THEN** the system SHALL log the failure without rolling back the payment action.
