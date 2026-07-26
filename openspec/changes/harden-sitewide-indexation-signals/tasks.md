## 1. Metadata and route rendering

- [x] 1.1 Add shared public and noindex metadata builders.
- [x] 1.2 Move interactive route implementations behind server page/layout boundaries.
- [x] 1.3 Add self-canonical metadata to all static sitemap routes.
- [x] 1.4 Canonicalize recognized product family query URLs to category hubs.
- [x] 1.5 Apply the required robots directives to purchase and private routes.

## 2. Canonical content and discovery

- [x] 2.1 Render actual family products and Product ItemList data on category hubs.
- [x] 2.2 Remove thin 'coming soon' copy from indexable category surfaces.
- [x] 2.3 Link the primary category navigation to canonical family URLs.
- [x] 2.4 Normalize and deduplicate sitemap output while excluding non-indexable routes.

## 3. Robots persistence

- [x] 3.1 Keep noindex routes crawlable in the frontend robots response and always advertise sitemap.xml.
- [x] 3.2 Change the Django robots default and migrate persisted legacy blocks.
- [x] 3.3 Update the robots endpoint regression test.

## 4. Verification and delivery

- [x] 4.1 Add and run frontend SEO policy regression tests.
- [x] 4.2 Verify canonical, robots, and H1 values against production-build HTML.
- [x] 4.3 Run the targeted Django test, system checks, migration checks, frontend lint, and production build.
- [x] 4.4 Validate this OpenSpec change in strict mode.
- [x] 4.5 Pull, commit, push both repositories, and rebuild manual deployment archives.
