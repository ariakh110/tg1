# Change: Harden sitewide indexation signals

## Why

Search Console and live-page inspection showed inconsistent indexation signals across public, filtered, transactional, authentication, and account routes. Several public pages lacked self-canonical metadata, filtered product URLs competed with category hubs, private workflows were indexable, and robots rules prevented crawlers from seeing intended `noindex` directives.

## What Changes

- Add a shared server-side metadata policy for indexable public routes with unique title, description, self-canonical, Open Graph, Twitter, and explicit `index,follow` directives.
- Canonicalize `/products?family=<family>` to `/category/<family>` for the six established product families and taxonomy-defined active roots.
- Render `/products` through a server route so its H1 and initial page structure exist in the response HTML.
- Mark product purchase flows as `noindex,follow`; mark authentication, account, admin, cart, checkout, private order, and offer flows as `noindex,nofollow`.
- Keep noindex routes crawlable in `robots.txt`, migrate legacy robots settings, and retain the `/api/` crawl block.
- Limit `sitemap.xml` to same-origin, query-free, unique, indexable canonical URLs.
- Replace thin category placeholders with a server-rendered product list, prices or enquiry state, product links, and Product ItemList data.
- Point primary navigation links at canonical category hubs while retaining the advanced filtered product interface.

## Impact

- Frontend: Next.js App Router metadata, route shells, category pages, sitemap, robots route, and SEO regression tests.
- Backend: default robots configuration, data migration, and content-management endpoint test.
- Data migration: `blog.0010_allow_noindex_routes_in_robots` removes legacy blocks only for routes that now expose meta robots directives.
