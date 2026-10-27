## ADDED Requirements

### Requirement: Fast multi-category purchase list
Customers SHALL add, duplicate, delete or atomically import 1–50 requested items across active catalog categories, enter contact details once and verify one immutable list by SMS. Each item SHALL preserve category, specifications, positive quantity and explicit unit. No catalog product SHALL be created.

#### Scenario: Several product families
- **WHEN** a customer requests sheets, rebar and pipe in one list
- **THEN** all items are visible for review and receive one phone-verification flow

#### Scenario: Invalid bulk paste
- **WHEN** an imported row has an invalid category, unit or quantity
- **THEN** an explanatory row error appears and no partial rows are appended

### Requirement: One verified sales request
Successful verification SHALL atomically create one AssistantInquiry and CRM lead/opportunity, retaining all structured requested_items and returning one reference. Repeated verification SHALL return the same reference. Existing single-item submissions SHALL remain supported. Details changed under the same request ID SHALL be rejected; invalid or oversized lists SHALL never trigger paid SMS.

#### Scenario: Verified large list and retry
- **WHEN** a correct SMS code verifies a 50-item list twice
- **THEN** exactly one inquiry contains all 50 items and one reference is returned both times

#### Scenario: Customer edits before sending again
- **WHEN** the list or contact details change after code request
- **THEN** the UI uses a new request ID and the original OTP cannot authorize changed details
