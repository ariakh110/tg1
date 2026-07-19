## 1. Documentation

- [x] 1.1 Define featured-image and positioned-inline-image behavior.
- [x] 1.2 Update the content-management PRD and acceptance criteria.

## 2. Backend

- [x] 2.1 Validate blog image formats and size on post and media serializers.
- [x] 2.2 Remove replaced featured-image files after successful updates.
- [x] 2.3 Preserve inline image order and fallback alt text in generated HTML.
- [x] 2.4 Add API and rendering regression tests.

## 3. Frontend

- [x] 3.1 Add featured-image selection, preview, upload, replacement, removal, and alt controls.
- [x] 3.2 Enable Editor.js image uploads at the selected block.
- [x] 3.3 Add explicit quick-upload placement controls and accurate success feedback.
- [x] 3.4 Improve inline figure/caption rendering in preview and public articles.

## 4. Verification And Delivery

- [x] 4.1 Run OpenSpec validation, Django checks/tests, frontend lint, and production build.
- [x] 4.2 Verify the editor workflow in desktop and mobile browser views.
- [x] 4.3 Commit, synchronize, and push both repositories.
- [x] 4.4 Refresh the manual-deployment archives.

## 5. Production Upload Hotfix

- [x] 5.1 Return structured JSON and roll back article changes when media storage is not writable.
- [x] 5.2 Keep a successful image replacement successful when cleanup of the obsolete file fails.
- [x] 5.3 Exclude runtime media from source archives and prepare writable media directories during deployment.
- [x] 5.4 Show a useful Persian error when a proxy or server returns a non-JSON 5xx response.
- [x] 5.5 Run regression checks, synchronize GitHub, and rebuild the manual deployment archives.
