## MODIFIED Requirements

### Requirement: Settlement Term Fee
The system SHALL model settlement deadline and extra fee for multi-day settlement terms and SHALL support payment-link or Satna settlement methods.

#### Scenario: Buyer chooses Satna settlement
- **WHEN** a buyer submits direct checkout with Satna selected
- **THEN** the direct order SHALL retain its settlement-term fee
- **AND** the Satna deadline SHALL use the selected due date at 10:00 Asia/Tehran.
