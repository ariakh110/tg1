## ADDED Requirements

### Requirement: Customer Records
The system SHALL maintain CRM customer records that are independent of website user accounts. Each customer SHALL have a name and a unique normalized phone number used as the primary identifier, plus optional company, city/province, free note, additional phone numbers, and an optional link to a website user. Admins SHALL create, view, update, deactivate, and search customers by name, phone, or company. The phone number SHALL be unique so that a later incoming call can be matched to exactly one customer.

#### Scenario: Create and find a phone customer
- **WHEN** an admin creates a customer «حسن رضایی / 09120000000 / شرکت فولاد آریا»
- **THEN** the customer is stored, appears in the customer list, and is found when the admin searches by name, by the phone number, or by the company name

#### Scenario: Duplicate phone is rejected
- **WHEN** an admin tries to create a second customer with a phone number that already exists
- **THEN** the system rejects it so the same phone never maps to two customers

### Requirement: Customer Ledger and Balance
The system SHALL record customer transactions in a single ledger where each entry is a purchase (خرید), a payment (پرداخت), or an adjustment (تعدیل/مانده اولیه), with an amount in Toman and an optional free‑text description of what was bought. The customer's balance SHALL be computed as the sum of purchases minus the sum of payments plus the sum of adjustments, where a positive balance means the customer owes the business. Purchases and payments SHALL require a positive amount; adjustments MAY be negative. Each customer view SHALL expose the current balance, and the customer's transactions SHALL be listable newest‑first.

#### Scenario: Balance reflects purchases and payments
- **WHEN** a customer has a purchase of 10,000,000 («۲۰ تن میلگرد ۱۴») and a payment of 4,000,000
- **THEN** the customer's balance is 6,000,000 (still owed) and both rows are visible in the customer's transaction history with their descriptions

#### Scenario: Settled customer shows zero
- **WHEN** total payments equal total purchases for a customer
- **THEN** the balance is 0

### Requirement: Admin-only Access
The CRM customer and transaction APIs SHALL be accessible only to admin users (staff/superuser or an active admin role), consistent with the rest of the admin surface, and SHALL NOT be exposed to public or ordinary authenticated website users.

#### Scenario: Non-admin is denied
- **WHEN** an unauthenticated or non‑admin user requests the CRM customers or transactions endpoint
- **THEN** the request is denied
