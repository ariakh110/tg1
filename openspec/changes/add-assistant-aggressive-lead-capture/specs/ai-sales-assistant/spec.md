## ADDED Requirements

### Requirement: Configurable Lead-Capture Intensity
The sales assistant SHALL support an admin-configured intensity for collecting the customer's full name and mobile number, with three levels: off (only when volunteered), soft (persistent benefit-framed persuasion), and strict (the assistant withholds an exact price or proforma until name and mobile are captured). The chosen level SHALL shape the assistant's system prompt, and once a phone is already captured for a conversation the assistant SHALL stop asking.

#### Scenario: Soft mode pushes for contact
- **WHEN** the assistant runs in soft mode and a visitor asks about a product
- **THEN** the assistant's instructions direct it to ask for the customer's full name and mobile, framed as a benefit, and to re-ask politely if dodged

#### Scenario: Already-captured stops the asking
- **WHEN** the conversation already has a stored phone number
- **THEN** the assistant is told the contact is on file and not to ask again

### Requirement: Strict-Mode Price Gate
In strict mode, the assistant SHALL NOT return an exact price quote until the conversation has a captured phone number; the price tool SHALL return a gating result that instructs the assistant to capture the lead first, and SHALL return prices normally once a phone is present.

#### Scenario: Price withheld until lead captured
- **WHEN** the price tool is invoked in strict mode for a conversation with no captured phone
- **THEN** it returns a gating result instead of a price, instructing the assistant to collect name and mobile first

#### Scenario: Price flows after capture
- **WHEN** the price tool is invoked in strict mode after the conversation has a captured phone
- **THEN** it is not gated and proceeds to quote

### Requirement: Validated Contact Capture
Capturing a lead SHALL require a non-empty full name and a valid Iranian mobile number, and SHALL store the mobile normalized to the `09XXXXXXXXX` form; an invalid or incomplete phone SHALL be rejected so the assistant asks again.

#### Scenario: Invalid phone is rejected
- **WHEN** the assistant tries to capture a lead with an incomplete phone number
- **THEN** the capture is rejected with a message to obtain a complete mobile, and nothing is stored

#### Scenario: International form is normalized
- **WHEN** a lead is captured with a `+98…` mobile and a full name
- **THEN** the stored phone is the `09XXXXXXXXX` form and the name is saved
