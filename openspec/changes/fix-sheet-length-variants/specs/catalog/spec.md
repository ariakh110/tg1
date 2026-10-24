## ADDED Requirements
### Requirement: Independent physical variants
The system SHALL preserve same-name products with different supplied specifications and SHALL reject ambiguous implicit updates.
#### Scenario: Different sheet lengths
- **WHEN** an admin creates 6000mm and over-7000mm sheets with the same name
- **THEN** separate products, specifications and prices are retained
### Requirement: Variable sheet length
The system SHALL distinguish exact length from a strictly greater-than threshold, label it publicly, and SHALL NOT estimate an exact unit weight from that threshold.
#### Scenario: Over seven metres
- **WHEN** length_type is over and length_mm is 7000
- **THEN** the UI displays a variable length over 7000mm and does not use 7000mm as an exact unit weight
