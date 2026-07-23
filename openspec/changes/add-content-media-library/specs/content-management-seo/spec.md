## ADDED Requirements

### Requirement: Reusable Content Media Library
The system SHALL provide authorized content authors with a searchable media library and SHALL allow an existing image to be reused safely as inline article media or as a post featured image.

#### Scenario: Author browses uploaded images
- **WHEN** an authorized author opens the media library
- **THEN** the system SHALL show uploaded images newest-first with preview, alt text, upload date, search, and bounded pagination.

#### Scenario: Author uploads through the media library
- **WHEN** an author uploads a valid image with alt text from the media-library dialog
- **THEN** the new asset SHALL be stored once and SHALL appear in the library for immediate reuse.

#### Scenario: Author reuses an image inside article text
- **WHEN** an author chooses a library image for inline insertion
- **THEN** the system SHALL insert its existing URL and alt text at the chosen Editor.js placement without uploading a duplicate binary.

#### Scenario: Author reuses an image as the featured image
- **WHEN** an author chooses a library image as a post featured image
- **THEN** the system SHALL create an independent post thumbnail copy so later post-image replacement or removal SHALL NOT delete the shared library asset.
