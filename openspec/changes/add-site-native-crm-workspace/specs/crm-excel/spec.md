## ADDED Requirements

### Requirement: Versioned CRM Workbook Export
The system SHALL export a versioned Excel workbook derived from the supplied 33-sheet CRM template. The workbook SHALL include schema metadata, data dictionary, controlled lists, Persian labels, validations, formulas/dashboard where supported, editable CRM data, and read-only projections of website users, products, orders, quote data, payments, shipments, and audit. Stable database identifiers MUST be included for round-trip matching.

#### Scenario: Export reflects website records
- **WHEN** an admin exports the CRM workbook
- **THEN** customers, leads, opportunities, follow-ups, and interactions are populated from CRM
- **AND** products, direct orders, payments, and shipments are populated from their authoritative website models

### Requirement: Previewed and Confirmed Safe Import
CRM workbook import SHALL require a preview before apply. Preview SHALL verify schema version and file integrity and report create, update, skip, and error counts with per-row details. Apply SHALL require the matching preview token/file hash, write only whitelisted CRM fields, preserve fields for blank cells, normalize identifiers and phones, prevent duplicates, and audit every applied or rejected row.

#### Scenario: Blank cell preserves existing value
- **WHEN** an imported customer or opportunity row leaves an optional editable cell blank
- **THEN** the existing database value is unchanged unless the workbook contains the explicit supported clear marker

#### Scenario: Stale preview cannot apply
- **WHEN** the uploaded file differs from the file that produced the preview
- **THEN** apply is rejected and a new preview is required

#### Scenario: One bad row does not hide the result
- **WHEN** a workbook contains valid and invalid CRM rows
- **THEN** preview reports each row result precisely
- **AND** apply follows the documented row/transaction policy without silently losing valid data

### Requirement: Transactional Sheets Are Import Read-Only
Workbook sheets projecting products, product prices, direct orders, order items, quote amounts/status, payments, inventory, shipments, users, and audit SHALL be read-only for CRM import. Any attempted change to protected transactional values MUST be rejected and audited. Such data may only change through its owning website workflow and domain services.

#### Scenario: Workbook attempts to mark an order paid
- **WHEN** an uploaded workbook changes a payment or order-status cell
- **THEN** import rejects the change, records the protected-field error, and leaves the authoritative records unchanged

### Requirement: Excel Operations Are Admin-Scoped and Audited
Export, preview, and apply endpoints SHALL require the appropriate CRM admin section. The system SHALL record actor, timestamp, file hash, schema version, row counts, outcome, and retained error report while limiting temporary file retention and preventing secrets from appearing in the workbook.

#### Scenario: Marketer lacks Excel apply permission
- **WHEN** a role with CRM viewing but without CRM import permission attempts to apply a workbook
- **THEN** the operation is denied and no row changes
