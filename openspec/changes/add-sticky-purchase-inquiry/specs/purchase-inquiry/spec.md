## ADDED Requirements

### Requirement: Storefront Sticky Purchase Inquiry
The storefront SHALL show an accessible sticky purchase-inquiry action above mobile navigation, independently of the chat assistant, and SHALL hide it in account, checkout, authentication and admin workspaces.

#### Scenario: Visitor opens the form
- **WHEN** the visitor activates the sticky inquiry button
- **THEN** a modal displays product, size, kilogram quantity, optional city/name and mobile fields
- **AND** focus remains inside the dialog until closing returns focus to its trigger

### Requirement: Phone Verified Inquiry Intake
The system SHALL create a purchase inquiry and CRM lead only after successful SMS code verification for the immutable submitted details.

#### Scenario: A valid code is entered twice
- **WHEN** the same request and correct code are verified more than once
- **THEN** exactly one inquiry is stored and the existing reference is returned

#### Scenario: A code is wrong or expired
- **WHEN** a code has expired or five wrong attempts have occurred
- **THEN** no inquiry is created

### Requirement: Bounded Confidential OTP Delivery
The system SHALL hash codes, redact SMS log bodies, enforce cooldowns and phone/IP/global quotas, and refuse paid sending when quota storage or SMS configuration is unavailable.

#### Scenario: SMS configuration is missing
- **WHEN** SMS is disabled or the provider key is unavailable
- **THEN** the form explains temporary unavailability without pretending a code was delivered

#### Scenario: Resend is requested too soon
- **WHEN** another SMS is requested before the cooldown ends
- **THEN** no new SMS is sent and a retry delay is returned
