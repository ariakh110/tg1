# Change: Add content management and SEO core

## Why

The public blog already exposes published posts, but content operators cannot create, review, schedule, publish, or optimize articles from the application. The attached PRD defines a broader CMS roadmap; this change delivers the operational core without introducing infrastructure dependencies such as Redis, Celery, S3, or search services.

## What Changes

- Extend blog posts with workflow, excerpt, SEO metadata, robots directives, Open Graph fields, scheduled publishing, and SEO score.
- Add admin content CRUD, publish/schedule, revision history, revision restore, SEO analysis, media upload, sitemap, schema, and robots endpoints.
- Add a dedicated `/admin/content` editor with draft auto-save, HTML preview, SEO feedback, publish/schedule actions, and revision restore.
- Switch public blog fetching to ISR-compatible caching and emit article JSON-LD, root sitemap, and robots metadata.
- Preserve existing `/api/blog/posts/` and `/api/blog/categories/` public contracts.
- Add Editor.js block authoring while preserving sanitized HTML for public rendering.
- Add inline category creation with automatic selection.
- Add reviewable AI suggestions for excerpt and keywords through the OpenAI Responses API.

## Impact

- Affected specs: `content-management-seo`
- Affected backend: `blog` models, serializers, views, URLs, migrations, tests
- Affected frontend: public blog metadata/rendering and new admin content editor
- Database migration required.
