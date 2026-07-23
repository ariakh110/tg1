# Change: Add content media library

## Why

Article images can be uploaded, but authors cannot browse previous uploads or reuse them. Re-uploading the same image creates unnecessary copies and makes long-form article production slower.

## What Changes

- Add an authenticated, searchable, paginated media library to `/admin/content`.
- Let authors upload a new image directly into the library and immediately see it in the list.
- Let an existing library image be inserted at the selected Editor.js position or at the end of the article.
- Let an existing library image become a post featured image through a server-side independent copy, preserving the shared library file.
- Keep existing file validation, alt-text requirements, public URLs, and article rendering behavior.

## Impact

- Affected spec: `content-management-seo`
- Affected backend: blog media listing, post media action, and API tests
- Affected frontend: content API helpers and the content-management media-library dialog
- Database migrations: none
