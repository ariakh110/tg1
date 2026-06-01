## Context

The repository already has a Django `blog` app, CKEditor-backed HTML content, sanitized public serialization, and Next.js public blog pages. The CMS core should build on those contracts and remain deployable without Redis, Celery, object storage, or third-party SEO services.

## Goals / Non-Goals

- Goals: operational article management, workflow, SEO feedback, revision recovery, crawl metadata, and ISR-ready public rendering.
- Non-goals: AI generation of the main article body, distributed image processing, Google Indexing API, analytics dashboards, i18n translation workflow, and internal-link NLP recommendations.

## Decisions

- Extend the existing `Post` model instead of introducing a parallel content model, preserving current public blog URLs.
- Persist Editor.js block JSON beside sanitized HTML. The admin editor writes structured blocks, public pages keep rendering HTML, and CKEditor remains available in Django admin.
- Keep category creation behind the existing admin permission and select newly created categories in the editor UI.
- Call the OpenAI Responses API from Django only; API keys never reach the browser and suggestions never overwrite author fields without confirmation.
- Store SEO metadata on `Post` to remain compatible with existing `meta_title`, `meta_description`, and `canonical_url` fields.
- Compute SEO analysis synchronously for deterministic real-time feedback; persist the latest score on save.
- Store immutable `PostRevision` snapshots before updates and expose restore through an admin-only action.
- Generate schema, sitemap data, and robots text synchronously; asynchronous rebuilds remain a later infrastructure phase.

## Risks / Trade-offs

- The initial Editor.js toolset intentionally stays small. More block plugins can be added without changing public rendering contracts.
- Synchronous SEO analysis is appropriate for current scale but should move to cached/background processing if content volume grows.
- Local media upload is retained for the current deployment model; S3/CDN optimization remains a later phase.

## Migration Plan

Apply the additive blog migration, deploy backend endpoints, then deploy the Next.js admin editor and public metadata routes. Existing published posts remain publicly accessible.

## AI Configuration

- Set `OPENAI_API_KEY` on the Django server to enable metadata suggestions.
- Optionally set `OPENAI_CONTENT_MODEL`; the default is `gpt-5-mini`.
- Optionally set `OPENAI_API_TIMEOUT_SECONDS`; the default is `30`.
