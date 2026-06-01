## ADDED Requirements

### Requirement: Admin Article Management
The system SHALL allow authorized administrators to create, edit, review, schedule, publish, archive, and recover article content without changing the existing public blog URL contract.

#### Scenario: Admin saves a draft
- **WHEN** an administrator creates or edits an article without publishing it
- **THEN** the system SHALL persist the draft and keep it out of the public post list.

#### Scenario: Admin publishes an article
- **WHEN** an administrator publishes an approved article immediately or schedules a future publication time
- **THEN** the public API SHALL expose the article only after its effective publication time.

#### Scenario: Admin restores a previous revision
- **WHEN** an administrator restores a recorded article revision
- **THEN** the article SHALL recover the revision content and retain an audit snapshot of the replaced state.

### Requirement: Article SEO Feedback
The system SHALL store article SEO metadata and provide field-level SEO analysis with a score from zero to one hundred.

#### Scenario: Admin analyzes article SEO
- **WHEN** an administrator requests SEO analysis for an article
- **THEN** the response SHALL include the total score and checks for keyword placement, content structure, image alt text, internal links, keyword density, and schema availability.

### Requirement: Crawl Metadata
The system SHALL expose schema, sitemap, and robots data for public crawl surfaces.

#### Scenario: Crawler requests published article schema
- **WHEN** a crawler requests schema for a published indexable article
- **THEN** the system SHALL return Article-compatible JSON-LD containing canonical URL, author, and publication timestamps.

#### Scenario: Crawler requests sitemap
- **WHEN** a crawler requests sitemap data
- **THEN** the system SHALL list only published, effective, indexable articles with accurate modification timestamps.

### Requirement: Admin Category Creation
The system SHALL allow an authorized author to create a missing article category while editing an article and SHALL select the created category automatically.

#### Scenario: Author creates a missing category
- **WHEN** category search has no matching result and the author submits a new category
- **THEN** the system SHALL persist the category, close the creation modal, and select the new category for the current article.

### Requirement: Structured Article Authoring
The system SHALL use Editor.js blocks as the admin authoring format while retaining sanitized HTML for public rendering.

#### Scenario: Author saves Editor.js content
- **WHEN** an author saves supported Editor.js blocks
- **THEN** the system SHALL persist the blocks and generate sanitized HTML for public article pages and SEO analysis.

### Requirement: AI Metadata Suggestions
The system SHALL let an authorized author request AI-generated excerpt and keyword suggestions from the article title and main content.

#### Scenario: Author requests suggestions
- **WHEN** an author requests AI suggestions after writing the article body
- **THEN** the system SHALL return an excerpt, a focus keyword, and secondary keywords without overwriting article metadata automatically.

#### Scenario: OpenAI key is not configured
- **WHEN** an author requests suggestions and `OPENAI_API_KEY` is missing
- **THEN** the system SHALL return a Persian configuration error without modifying the article.
