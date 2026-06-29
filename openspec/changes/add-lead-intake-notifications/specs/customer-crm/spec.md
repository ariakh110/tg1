## ADDED Requirements

### Requirement: Automatic Lead Intake from Site Events
The system SHALL create or update a CRM customer automatically when a lead arrives through a site event — a user registration, a submitted direct-sales order, or a sales-chat lead — keyed by the normalized phone number. When a matching customer already exists, intake SHALL only fill blank fields (name, company, city, linked user) and SHALL NOT overwrite the stage or source an admin has already set. Each intake SHALL record on the customer's timeline how the lead arrived, and SHALL tag the customer's source as the originating channel (`website` for registration, `store_purchase` for an order, `chat` for the sales chat). When the event carries no usable phone number, no customer SHALL be created. Intake SHALL never break the originating action (signup, checkout, or chat).

#### Scenario: Registration creates a website lead
- **WHEN** a visitor registers on the site with phone `09120000001`
- **THEN** a CRM customer with that phone and source «ثبت‌نام سایت» exists, with a timeline note that it was added via site registration

#### Scenario: Order submission creates a purchase lead
- **WHEN** a buyer submits a direct-sales order with contact phone `09120000002`
- **THEN** a CRM customer with that phone and source «خرید از سایت» exists

#### Scenario: Existing customer keeps its admin-set stage and source
- **WHEN** an event arrives for a phone that already belongs to a customer the admin moved to stage `proposal` with source `referral`
- **THEN** the customer's stage stays `proposal` and source stays `referral`, and only previously blank fields are filled

#### Scenario: No phone, no customer
- **WHEN** a registration completes without any phone number
- **THEN** no CRM customer is created for it

### Requirement: Lead Registrar Tracking
Each CRM customer SHALL record who entered it: the admin user on a manual create, and empty (system) when it was created automatically from a site event. The customer read API SHALL expose a human-readable registrar name. The registrar SHALL NOT be settable by the client.

#### Scenario: Manual create records the admin
- **WHEN** an admin creates a customer through the CRM
- **THEN** the customer's registrar is that admin and the API returns the admin's display name

#### Scenario: Automatic intake has no registrar
- **WHEN** a customer is created automatically from a registration or order
- **THEN** the customer's registrar is empty, marking it as system-created
