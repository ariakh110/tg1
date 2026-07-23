## Context

`MediaAsset` already stores uploaded article images with alt text, title, caption, author, and creation time. Inline Editor.js image blocks reference a media URL. `Post.thumbnail`, however, owns its file and deletes the old file when replaced, so directly pointing it at a shared media asset would make later cleanup unsafe.

## Decisions

### MediaAsset remains the library source of truth

The existing admin media endpoint lists assets newest-first and supports a `q` search over alt text, title, caption, and file name. Standard pagination bounds the response while the dialog exposes previous and next controls.

### Inline reuse keeps one shared binary

Selecting «درج در متن» inserts the existing media URL as an Editor.js image block. The selected placement and asset alt text are retained, and no second binary is created.

### Featured-image reuse creates an independent copy

Selecting «تصویر اصلی» calls a post action with the media id. The backend reads the validated asset and saves a copy through the existing `AdminPostSerializer`. The post can then replace or remove its thumbnail without deleting the library source or breaking another article.

### Upload is available inside the dialog

The dialog uses the existing multipart media endpoint and existing JPEG/PNG/WebP and 5 MB validation. A successful upload refreshes the first result page, making the new asset immediately reusable.

## Risks

- Inline article blocks depend on the shared media URL; destructive media deletion is intentionally not exposed in this dialog.
- A legacy asset that no longer exists on storage returns the existing structured media-storage error when selected as a featured image.
- The modal requests at most 24 assets per page to keep image-heavy screens responsive.
