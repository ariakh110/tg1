## ADDED Requirements

### Requirement: Admin-Managed Messaging Settings
The system SHALL store messaging configuration in a single admin-managed settings record: a master `sms_enabled` switch (default off), the active `provider` (default Kavenegar), the Kavenegar API key, a default sender line, optional `verify/lookup` template names (a default template and a purchase-step template), and a `daily_send_cap` safety limit. The API key SHALL be write-only — never returned by the read endpoint — and the settings response SHALL instead expose a boolean indicating whether a key is configured. Only admin users SHALL read or update these settings.

#### Scenario: Key is write-only
- **WHEN** an admin saves a Kavenegar API key and then reads the messaging settings
- **THEN** the saved key is not present in the response, but a flag reports that a key is configured

#### Scenario: Empty key keeps the existing one
- **WHEN** an admin updates settings (e.g. toggles the sender line) without sending a key value
- **THEN** the previously saved API key is left unchanged

### Requirement: Provider-Agnostic SMS Sending with Dry-Run
The system SHALL send SMS through a configurable provider, gated by the master switch and a configured key. When messaging is disabled or no key is configured, a send SHALL be recorded as `skipped` (dry-run) with no error and SHALL NOT contact any provider, so the full send flow is testable before credentials exist. When enabled and configured, the system SHALL call the provider, and SHALL record the resulting status, provider message id, and cost; a provider-level failure (e.g. insufficient credit, invalid recipient) SHALL be captured as a failed message with its error rather than raising an unhandled error. Recipient phone numbers SHALL be normalized to the Iranian `09XXXXXXXXX` form before sending and logging.

#### Scenario: Dry-run when disabled
- **WHEN** an admin sends an SMS while `sms_enabled` is off (or no key is set)
- **THEN** an outbound message is logged with status `skipped`, no provider is contacted, and no error is reported

#### Scenario: Real send records provider result
- **WHEN** messaging is enabled and configured and a send succeeds
- **THEN** the outbound message status becomes `sent`, and the provider message id and cost are stored on the log row

#### Scenario: Provider failure is captured
- **WHEN** the provider rejects a send (e.g. insufficient credit)
- **THEN** the outbound message is recorded as `failed` with the provider error text, and the request itself still completes successfully

### Requirement: Send SMS to CRM Customers
Admins SHALL send a single SMS to a CRM customer (identified by customer id or by an explicit recipient phone) and SHALL send to a segment of customers selected by ids or by a stage/source/active filter. Every send to a customer SHALL append a `message` activity to that customer's timeline noting the message, so the CRM history reflects outbound contact. Bulk sending SHALL honor the configured daily send cap.

#### Scenario: Single send logs a customer activity
- **WHEN** an admin sends an SMS to customer «حسن رضایی»
- **THEN** an outbound message is logged for that customer and a `message` activity appears on the customer's timeline

#### Scenario: Segment send
- **WHEN** an admin sends a message to all customers in stage `proposal`
- **THEN** one outbound message is logged per matching customer

### Requirement: Purchase-Step Notifications
The system SHALL let admins send a purchase-step SMS to a customer for direct sales (for example: order registered, in preparation, shipped, delivered), rendered from a step template and optionally including an order number and amount. The send SHALL be logged with purpose `order_status` and, when a Kavenegar `verify/lookup` template is configured, SHALL use the template path so the message is not subject to the advertising filter.

#### Scenario: Send a shipped-step notification
- **WHEN** an admin sends the «ارسال شد» purchase step to a customer for order `1024`
- **THEN** an outbound message with purpose `order_status` is logged for that customer with the rendered step text

### Requirement: Outbound Message Log
The system SHALL record every send attempt as an outbound message with its channel, provider, recipient, purpose, body, status, provider message id, cost, error, optional linked customer, and creating admin, with timestamps. The log SHALL be listable newest-first and filterable by channel, status, purpose, and customer, and SHALL be readable only by admins.

#### Scenario: Log is filterable
- **WHEN** an admin lists outbound messages filtered by status `failed`
- **THEN** only failed messages are returned, newest first

### Requirement: Inbound Kavenegar Webhooks
The system SHALL expose two public Kavenegar callback endpoints, each guarded by a secret embedded in the URL path: a **delivery-status** callback that updates the matching outbound message's status from the Kavenegar status code (e.g. delivered, failed), and an **incoming-SMS** callback that, when the sender phone matches a CRM customer, appends a received-message activity to that customer's timeline. The webhook secret SHALL be auto-generated and readable by admins so the callback URLs can be configured in the Kavenegar panel. Requests with a missing or wrong secret SHALL be rejected.

#### Scenario: Delivery status updates the log
- **WHEN** Kavenegar calls the status webhook (with the correct secret) reporting message id `999` as delivered (code 10)
- **THEN** the outbound message with that provider message id becomes `delivered`

#### Scenario: Wrong secret is rejected
- **WHEN** a request hits a webhook URL with an incorrect secret
- **THEN** it is rejected with 403 and nothing is changed

#### Scenario: Incoming SMS from a known customer is logged
- **WHEN** Kavenegar delivers an incoming SMS from a phone that matches a CRM customer
- **THEN** a received-message activity is appended to that customer's timeline

### Requirement: Admin-only Messaging Access
All messaging settings, sending, and log APIs SHALL be accessible only to admin users (staff/superuser or an active admin role) and SHALL be surfaced as a `messaging` admin section available to the marketer role. They SHALL NOT be exposed to public or ordinary authenticated website users.

#### Scenario: Non-admin is denied
- **WHEN** an unauthenticated or non-admin user calls any messaging endpoint
- **THEN** the request is denied
