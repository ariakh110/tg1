## ADDED Requirements

### Requirement: Public FAQ Listing
The system SHALL expose `GET /api/blog/faqs/` returning all **active** FAQ items (each with `category`, `question`, `answer`, `sort_order`), ordered by category then sort order. The endpoint SHALL be publicly readable.

#### Scenario: Read active FAQs
- **WHEN** any client GETs `/api/blog/faqs/`
- **THEN** the response is HTTP 200 with the active FAQ items
- **AND** inactive items are not included

#### Scenario: Grouped presentation
- **WHEN** the `/faq` page renders the items
- **THEN** items are grouped under their `category` headings

### Requirement: Admin FAQ Management
The system SHALL allow admin users to create, edit, delete, and toggle FAQ items via `/api/blog/admin/faqs/`. Non-admins SHALL be denied.

#### Scenario: Admin creates an FAQ
- **WHEN** an admin POSTs `{category, question, answer}` to `/api/blog/admin/faqs/`
- **THEN** the item is created and appears in the public listing when active

#### Scenario: Non-admin blocked
- **WHEN** an unauthenticated or non-admin client writes to `/api/blog/admin/faqs/`
- **THEN** the response is HTTP 401/403 and nothing changes

### Requirement: Seeded Starter Content
The system SHALL ship with starter FAQ content across the registration, ordering, payment, delivery, and support categories, editable from the admin panel.

#### Scenario: Starter content present
- **WHEN** the FAQ migrations are applied on a fresh database
- **THEN** the public listing returns the seeded questions grouped by their categories
