## ADDED Requirements

### Requirement: Customer and Opportunity Funnels Coexist
The system SHALL preserve the existing customer-stage funnel and its current KPIs while adding an independent opportunity/direct-sales funnel. A customer MAY have multiple leads and multiple open or closed opportunities at the same time. Moving or closing an opportunity MUST NOT automatically overwrite `Customer.stage` or change the existing customer-funnel statistics.

#### Scenario: One customer has two simultaneous needs
- **WHEN** one customer requests CK45 sheet and also creates a separate ST37 order
- **THEN** the CRM stores two opportunities that can occupy different stages
- **AND** the opportunity funnel counts both while the customer funnel counts one customer

#### Scenario: Existing customer funnel remains available
- **WHEN** the site-native opportunity funnel is enabled
- **THEN** the current customer funnel still returns the existing stages, customer counts, ledger KPIs, CLV, and follow-up metrics

#### Scenario: A lost deal does not rewrite the customer funnel
- **WHEN** one opportunity is closed as lost
- **THEN** the customer remains available for future opportunities
- **AND** its existing customer stage is not automatically changed

### Requirement: Site-Native Direct-Sales Pipeline
The CRM SHALL use stable direct-sales stages `new_inquiry`, `qualified`, `pricing`, `quote_sent`, `payment_pending`, `fulfillment`, `won`, and `lost`. Stage changes SHALL follow website events and SHALL record transition history with from/to stage, time, actor or system event, reason, and source metadata. Marketplace user-to-user activity MUST NOT be included in this funnel.

#### Scenario: Quote-needed website order enters pricing
- **WHEN** a direct `StoreOrder` is created with status `QUOTE_REQUESTED`
- **THEN** exactly one linked opportunity exists in `pricing`

#### Scenario: Direct priced checkout awaits payment
- **WHEN** a priced direct order is created without requiring an admin quote
- **THEN** its linked opportunity enters `payment_pending`

#### Scenario: Delivery wins the opportunity
- **WHEN** the linked direct order reaches `DELIVERED` or `COMPLETED`
- **THEN** the opportunity enters `won` and records the source order event

#### Scenario: Quote rejection reopens pricing
- **WHEN** a buyer rejects a sent quote and provides a reason or note
- **THEN** the opportunity returns from `quote_sent` to `pricing`
- **AND** it is not counted as lost

### Requirement: Idempotent Site Lead and Order Synchronization
Signup, assistant inquiry, direct-order, quote, payment, and fulfillment events SHALL synchronize to the CRM after their source transaction commits. Every source event SHALL have a stable unique key so retries or webhook replay cannot create duplicate leads, opportunities, activities, or transitions. CRM synchronization failure MUST NOT fail the originating signup, checkout, payment, or logistics operation and SHALL be recorded for retry.

#### Scenario: Order event is delivered twice
- **WHEN** the same order status-history event is processed twice
- **THEN** only one opportunity transition and one corresponding CRM event are stored

#### Scenario: CRM is temporarily unavailable
- **WHEN** CRM synchronization fails after an order commits
- **THEN** the order remains committed
- **AND** the failed CRM event is visible and retryable

### Requirement: Assigned Follow-Up Workflow
The CRM SHALL maintain follow-ups independently from interaction history, with customer, optional opportunity, assignee, due time, channel, purpose, status, result, sequence step, reminder metadata, and idempotency key. Open opportunities SHALL require an owner and next action/follow-up. Snoozing SHALL require a new due time, and closing an opportunity SHALL cancel its remaining open sequence steps.

#### Scenario: Snooze requires a new date
- **WHEN** a user tries to snooze a follow-up without selecting a new due time
- **THEN** the request is rejected and the original due time remains

#### Scenario: Won opportunity stops the sequence
- **WHEN** an opportunity becomes won
- **THEN** its open automated follow-ups are cancelled while completed history remains

### Requirement: CRM Reuses Transactional Website Records
CRM views SHALL project products, direct orders, quote data, payments, loading, weighbridge, freight, shipment, and delivery from their existing domain models. CRM actions that affect these domains MUST call the existing domain services and MUST NOT directly write transactional status or monetary fields. Direct-order analytics SHALL use IRR source values and explicitly convert only for Toman display.

#### Scenario: CRM displays payment status
- **WHEN** an admin opens an opportunity linked to a direct order
- **THEN** the displayed payment amount and status come from the order's payment records rather than a copied CRM payment row

#### Scenario: Unsafe direct status write is blocked
- **WHEN** a CRM or Excel request attempts to set a store order directly to paid or delivered
- **THEN** the request is rejected unless the appropriate payment/logistics domain service validates and performs the transition
