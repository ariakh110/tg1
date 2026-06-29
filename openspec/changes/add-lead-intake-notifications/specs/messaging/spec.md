## ADDED Requirements

### Requirement: Admin Notification Channels
The system SHALL let an admin configure where event notifications are delivered: a Telegram bot (a master `telegram_enabled` switch, a write-only bot token, and one or more destination chat ids), and/or an SMS phone number for the admin. The bot token SHALL be write-only — never returned by the read endpoint — and the settings response SHALL instead expose flags indicating whether a token is configured and whether Telegram is ready to send. The admin SHALL be able to enable or disable each event source independently (user signup, order submitted, chat lead). Only admin users SHALL read or update these settings.

#### Scenario: Bot token is write-only
- **WHEN** an admin saves a Telegram bot token and then reads the messaging settings
- **THEN** the saved token is not present in the response, but a flag reports that a token is configured

#### Scenario: Multiple chat destinations
- **WHEN** the admin sets the destination chat id field to two comma-separated ids and an event fires
- **THEN** the notification is sent once to each chat id

### Requirement: Event Notifications to the Admin
The system SHALL provide a single admin-notification entry point that fans a titled, multi-line event out to every configured admin channel — Telegram to each destination chat id and SMS to the admin phone — recording each attempt as an outbound message with purpose `admin_alert`. When no admin channel is configured, the notification SHALL be recorded once as `skipped` (dry-run) and SHALL contact no provider. Notifying the admin SHALL never raise into the originating request: a channel failure SHALL be captured as a failed message, not propagated.

#### Scenario: Dry-run when no channel configured
- **WHEN** an event notification is sent while neither Telegram nor an admin SMS phone is configured
- **THEN** exactly one outbound message is recorded with status `skipped` and purpose `admin_alert`, and no provider is contacted

#### Scenario: Telegram delivery per destination
- **WHEN** Telegram is enabled and configured with two chat ids and an event notification is sent
- **THEN** two outbound messages (channel `telegram`, purpose `admin_alert`) are recorded with the provider result

### Requirement: Admin Test Alert
The system SHALL expose an admin-only endpoint that sends a test notification through the configured admin channels and returns a per-channel summary, so the admin can verify the bot token / chat id / phone wiring after entering them.

#### Scenario: Test alert reports per-channel result
- **WHEN** an admin triggers the test alert
- **THEN** a notification is dispatched through every configured channel and the response lists each channel with its delivery status
