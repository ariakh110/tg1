## ADDED Requirements

### Requirement: Distinct Market Context Navigation
The system SHALL preserve the public catalog-backed dashboard as `بازار داخلی کاوه‌متال` and SHALL distinguish catalog, Iran Mercantile Exchange and global metals datasets in navigation, headings and source labels.

#### Scenario: Visitor switches market context
- **WHEN** a visitor moves between catalog, IME and global market pages
- **THEN** the selected context, data source, currency, unit and observation time remain explicit
- **AND** catalog prices are never labelled as commodity-exchange trades or global exchange prices

