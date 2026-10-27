## ADDED Requirements

### Requirement: Explicit submission outcomes and recovery
The client SHALL validate matrix responses against requested row keys, statuses and counts. Malformed successes SHALL show a visible failure. Uncertain create failures SHALL instruct the operator to preview existing products again without automatically repeating creation. Preview SHALL prominently explain invalid rows, all-existing results and the separate final registration step.

#### Scenario: Proxy HTML or malformed JSON after create
- **WHEN** create returns an unreadable, incomplete or mismatched response
- **THEN** form values remain, final confirmation is invalidated, and the operator is instructed to reconcile by preview

#### Scenario: Already created after lost connection
- **WHEN** a fresh preview finds every selected identity already present
- **THEN** it explicitly reports all-existing with IDs and does not permit duplicate creation

### Requirement: Automatic and manual product names
Matrices SHALL default to automatic names including grade. Operators MAY select manual mode with a nonempty trimmed row name of at most 255 characters. Name changes SHALL NOT affect physical identity or overwrite existing products. Invalid manual names SHALL reject the entire batch atomically.

#### Scenario: Manual names for two lengths
- **WHEN** ST52 Oxin products with width 2000 and lengths 6000 and 12000 are given manual names
- **THEN** each selected new identity retains its supplied name, and repeated submission skips both identities unchanged
