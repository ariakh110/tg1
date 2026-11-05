## ADDED Requirements

### Requirement: Source-traced angle and channel catalog
The catalog preparation SHALL include only observed angle and channel combinations,
preserve source references and distinguish duplicates from genuinely different specifications.

#### Scenario: Repeated product on factory and warehouse listings
- **WHEN** the same technical identity is observed at more than one source location or page
- **THEN** one candidate product SHALL retain every observation without creating a seller offer or a duplicate product.

#### Scenario: Grade tables without manufacturer columns
- **WHEN** a source table uses the grade column instead of a brand column
- **THEN** its rows SHALL be retained, explicit ST52/5SP SHALL map to steel_grade, and the unknown manufacturer SHALL NOT be invented.

### Requirement: Unknown and invalid technical facts
The preparation SHALL quarantine invalid source units/lengths and leave absent technical values unset.

#### Scenario: Nominal channel size and warehouse brand label
- **WHEN** a row gives nominal size and lists a warehouse in the brand column
- **THEN** nominal size SHALL remain a dynamic specification, measured height SHALL NOT be inferred, and warehouse SHALL NOT become a factory.

#### Scenario: Invalid unit or length
- **WHEN** a row contains a length string as its unit or a location as its length
- **THEN** it SHALL be quarantined with provenance and SHALL NOT enter the apply candidates.

### Requirement: Owned SEO and safe publication
Candidates SHALL carry original Persian content, stable internal slugs and supported native SEO fields, without copying foreign marketing, media, prices or stock claims.

#### Scenario: Unreviewed candidate
- **WHEN** a candidate is prepared or first imported
- **THEN** it SHALL remain inactive, inquiry-only and noindex, with an owned canonical path and no imported Offer or PricingTier.

### Requirement: Controlled offline seeding
After design approval, a seed operation SHALL support read-only preview and explicit atomic create-only application with auditable identity and a versioned local data file.

#### Scenario: Repeated update
- **WHEN** an already applied package is applied again after an administrator edits or deactivates a record
- **THEN** the operation SHALL preserve existing records and their edits and SHALL NOT create duplicates or overwrite content, prices or visibility.

#### Scenario: Conflicting existing identity
- **WHEN** a category, option, slug, technical identity or seed audit resolves ambiguously or contradicts the package
- **THEN** the operation SHALL report the conflict and leave the transaction unapplied rather than guessing a merge.

#### Scenario: Release without the external source
- **WHEN** the approved package is applied during an authorized update
- **THEN** the operation SHALL use local versioned data without network access and log created records and the batch hash.
