## Context

`Post.thumbnail` and public thumbnail rendering already exist. The missing part is an authenticated multipart workflow in the custom content editor. Inline images are already represented as Editor.js image blocks and rendered in sequence, but the editor disables the image toolbox and its imperative insertion method does not provide an index.

## Decisions

### Featured image uses the existing post endpoint

The frontend first persists pending article fields, then sends a multipart `PATCH` containing `thumbnail` and `thumbnail_alt` to the existing admin post endpoint. Removal uses a partial JSON update with `thumbnail: null`. This avoids a second image-specific backend route and requires no schema migration.

### Inline placement remains block-native

The Editor.js image tool uses the existing media endpoint. Its toolbox upload inserts at the block chosen in Editor.js. The quick uploader calculates an explicit insertion index from `getCurrentBlockIndex()` and also offers an end-of-document option. Stored block order remains the source of truth for generated HTML.

### Image validation is server authoritative

The browser performs an early type/size check for usability. DRF serializers enforce the same 5 MB limit and accept only Pillow-verified JPEG, PNG, and WebP content. SVG and GIF are rejected. Replaced or explicitly removed featured images are deleted from storage after a successful database update.

### Binary files are not revision snapshots

Post revisions continue to cover article text and metadata. Historical image binaries are not copied into revision snapshots; replacing or removing a featured image is therefore an explicit media operation outside revision restore.

### Runtime media is deployment state

The backend source archive excludes `media/`. The deployment updater preserves that directory, detects the systemd service user, creates the blog image subdirectories, restores ownership and write permissions, and verifies that the service user can write before restarting the backend. This prevents a root-owned source extraction from turning valid uploads into production 500 responses.

Storage write failures are translated to a JSON `503` response and the database update is rolled back. Failure to delete an obsolete image after a successful replacement is logged for later cleanup but does not turn the completed replacement into a failed request.

## Risks

- An author who has not selected an Editor.js block will get end-of-document insertion; the UI reports the actual placement.
- Existing image URLs remain valid and need no data migration.
- The media preparation script must run with permission to change ownership; the existing updater runs as root and satisfies that requirement.
