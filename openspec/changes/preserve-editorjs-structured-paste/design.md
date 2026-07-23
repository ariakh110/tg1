## Context

Editor.js only recognizes block types that have registered tools. The content editor registered headers, lists, quotes, raw HTML, and images but not tables, while both frontend and backend block renderers also omitted the `table` type. Rich clipboard payloads and tab-separated table text were therefore flattened.

## Goals / Non-Goals

- Goals: preserve table dimensions, headings, surrounding rich blocks, safe links, ordering, persistence, and responsive display.
- Goals: support both `text/html` tables and plain `text/plain` tab-separated tables.
- Non-Goals: reproduce all Microsoft Word visual styling, merged cells, arbitrary fonts, or page-layout metadata.

## Decisions

- Use the maintained official `@editorjs/table` tool for table editing and canonical Editor.js table data.
- Intercept paste only when an HTML table or tab-separated row is present; ordinary paste remains owned by Editor.js.
- Parse HTML clipboard content with `DOMParser`, preserving supported blocks and a minimal safe inline-tag set.
- Infer headings conservatively in tab-separated plain-text articles and retain unmatched lines as paragraphs with explicit line breaks.
- Store canonical table blocks in `content_blocks` and render them server-side into a `content-table-wrap` container before the existing Bleach sanitizer runs.
- Limit editable tables to 100 rows and 20 columns, and use local horizontal scrolling on narrow viewports.

## Risks / Trade-offs

- Clipboard HTML differs between browsers and office applications. The parser uses semantic tags and falls back to tab-separated text.
- Plain text has no definitive heading metadata. Heading inference only runs for a paste that also contains tabular rows.
- Complex merged cells are normalized into the table tool's rectangular matrix because Editor.js table data does not carry arbitrary office layout metadata.

## Migration Plan

No data migration is needed. Existing blocks continue to render unchanged; newly pasted table blocks use the already-present JSON field.

## Open Questions

- None.
