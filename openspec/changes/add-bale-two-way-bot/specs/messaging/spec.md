## ADDED Requirements

### Requirement: Two-Way Bot Webhook
The system SHALL accept Bale bot updates at a public endpoint guarded by the messaging webhook secret in its path, parse each update as a message or a button callback, and always respond success without letting any handler error escape. The system SHALL provide an admin-only action that registers this endpoint with Bale as the bot's webhook URL. Update handling SHALL be inert unless the two-way bot is explicitly enabled.

#### Scenario: Wrong secret is rejected
- **WHEN** a request hits the bot webhook with a secret that does not match the configured one
- **THEN** it is refused with a forbidden response and no update is processed

#### Scenario: Disabled bot ignores updates
- **WHEN** an update arrives while the two-way bot is disabled
- **THEN** the endpoint responds success but no command, reply, or CRM change happens

### Requirement: Inline CRM Action Buttons
When the two-way bot is enabled and a notification concerns a specific customer, the system SHALL attach inline action buttons to that notification, and clicking a button SHALL apply the action to that customer in the CRM: marking that a call was made, scheduling a next-day follow-up, or moving the customer to the won stage (recording a stage-change activity). Only an authorized sender SHALL be able to trigger a CRM-modifying action; an unauthorized click SHALL change nothing.

#### Scenario: Admin marks a lead as won from the group
- **WHEN** an authorized group member clicks «🤝 مشتری شد» on a lead notification
- **THEN** that customer's stage becomes «مشتری فعال» and a stage-change activity is recorded

#### Scenario: Unauthorized click is ignored
- **WHEN** a non-admin (not in the configured group and not a listed admin user) clicks an action button
- **THEN** the customer is unchanged and the click is acknowledged without applying anything

### Requirement: Admin Commands and Daily Digest
The system SHALL answer admin commands sent to the bot by an authorized sender: today's new leads with overdue/today follow-ups, a single customer's card looked up by phone, and the list of top debtors. The system SHALL also provide a command that composes the same daily summary and sends it to the configured admin channels, suitable for a scheduled run.

#### Scenario: Today command returns the digest
- **WHEN** an authorized sender sends the «امروز» command to the bot
- **THEN** the bot replies with today's new-lead count and the overdue/today follow-ups

#### Scenario: Customer lookup by phone
- **WHEN** an authorized sender sends the lead command with a phone number that belongs to a customer
- **THEN** the bot replies with that customer's name, stage, source, and balance

### Requirement: Customer Price Bot
The system SHALL treat any free-text (non-command) message to the bot as a product query, search the live catalog, and reply with the best matches including each product's price (or a quote-needed note) and a link, available to any user without authorization.

#### Scenario: Price query returns matches
- **WHEN** a user sends a product name such as «میلگرد ۱۴» to the bot
- **THEN** the bot replies with matching products and their prices or a «نیازمندِ استعلام» note
