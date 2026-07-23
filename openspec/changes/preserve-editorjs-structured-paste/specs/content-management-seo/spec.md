## ADDED Requirements

### Requirement: Structured Rich Paste And Tables
The content editor SHALL preserve supported structure when an author pastes an article containing tables and SHALL persist table blocks as sanitized, responsive public HTML.

#### Scenario: Author pastes rich HTML containing a table
- **WHEN** clipboard HTML contains headings, paragraphs, lists, links, and a table
- **THEN** the editor SHALL create corresponding blocks in source order and SHALL preserve table rows, columns, and heading-row semantics.

#### Scenario: Author pastes a tab-separated article
- **WHEN** rich clipboard HTML is unavailable and the plain text contains contiguous rows with tab-separated cells
- **THEN** the editor SHALL convert each tabular group into a rectangular table block without concatenating adjacent cells.

#### Scenario: Author pastes ordinary text
- **WHEN** clipboard content contains neither an HTML table nor tab-separated table rows
- **THEN** the editor SHALL retain its normal paste behavior without applying structured-table inference.

#### Scenario: Structured table is saved and published
- **WHEN** an article with a table block is saved
- **THEN** the backend SHALL retain canonical table block data and SHALL generate sanitized table HTML with an optional heading row.

#### Scenario: Table is viewed on a narrow screen
- **WHEN** an editor or reader views a table wider than the available viewport
- **THEN** the table SHALL scroll within its own content area and SHALL NOT create horizontal overflow for the full page.
