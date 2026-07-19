## MODIFIED Requirements

### Requirement: Structured Article Authoring
The system SHALL use Editor.js blocks as the admin authoring format while retaining sanitized HTML for public rendering, and SHALL let authorized authors manage a featured image and place inline images at a chosen block position.

#### Scenario: Author saves Editor.js content
- **WHEN** an author saves supported Editor.js blocks
- **THEN** the system SHALL persist the blocks in their authored order and generate sanitized HTML for public article pages and SEO analysis.

#### Scenario: Author manages the featured image
- **WHEN** an author uploads, replaces, or removes a valid featured image in the content editor
- **THEN** the existing post SHALL reflect that media change and the admin editor SHALL show the current or selected image preview and alt text.

#### Scenario: Author inserts an image within article text
- **WHEN** an author uploads an inline image at a selected Editor.js block or chooses a quick-upload placement
- **THEN** the image block SHALL be inserted at that position and its stored order SHALL be preserved in preview and public HTML.

#### Scenario: Author submits an unsafe or oversized blog image
- **WHEN** an author submits a blog image that is larger than 5 MB or is not a verified PNG, JPEG, or WebP file
- **THEN** the API SHALL reject the upload without changing the existing featured image or article content.

#### Scenario: Production media storage is prepared during deployment
- **WHEN** a backend source package is applied to production
- **THEN** runtime media SHALL be preserved outside the source archive and the article image directories SHALL be writable by the backend service account before it restarts.

#### Scenario: Media storage is temporarily unavailable
- **WHEN** an otherwise valid image cannot be written to media storage
- **THEN** the API SHALL return a structured service-unavailable response and SHALL leave the existing article image and revision history unchanged.
