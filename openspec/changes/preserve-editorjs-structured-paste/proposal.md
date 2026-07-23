# Change: Preserve structured content pasted into Editor.js

## Why

Pasting an article that contains comparison tables currently flattens every table row and cell into one paragraph. The resulting article is difficult to edit and the saved public HTML loses the source structure.

## What Changes

- Add the official Editor.js table tool to the content editor.
- Convert rich HTML paste containing tables into ordered Editor.js header, paragraph, list, quote, raw, and table blocks.
- Convert tab-separated plain-text tables into real table blocks when rich clipboard HTML is unavailable.
- Render table blocks as sanitized HTML in the backend and style them responsively in the editor and public article.
- Preserve normal Editor.js paste behavior for clipboard content that does not contain an HTML or tab-separated table.

## Impact

- Affected spec: `content-management-seo`
- Affected frontend: Editor.js configuration, structured-paste parser, admin HTML preview generation, and public article table styling
- Affected backend: Editor.js block renderer and blog regression tests
- New dependency: `@editorjs/table`
- Database migrations: none
