# Change: Enhance blog image authoring

## Why

The article model and public blog already support a featured image, but the content-management screen has no way to upload, replace, preview, or remove it. Inline image uploads are also appended without reliable control over their position, which prevents authors from laying out long articles correctly.

## What Changes

- Add featured-image upload, preview, replacement, removal, and alt-text controls to `/admin/content`.
- Let authors upload an image from the Editor.js toolbox at the selected block or use the quick uploader to insert after the active block or at the end.
- Keep inline image order in the stored Editor.js blocks and generated sanitized HTML.
- Validate featured, Open Graph, and inline blog images as PNG, JPEG, or WebP files no larger than 5 MB.
- Improve public article figure and caption presentation without changing existing blog URLs.

## Impact

- Affected specs: `content-management-seo`
- Affected backend: `blog/serializers.py`, `blog/editorjs.py`, `blog/tests.py`
- Affected frontend: admin content editor, content API helpers, and public article rendering
- Database migrations: none
