# Change: Server-rendered product pages + structured data (SEO phase 1)

## Why
Product detail pages were fully client-rendered (`"use client"` + `useEffect` fetch), so product name, price, and specs were absent from the initial HTML and there was no `generateMetadata` — Google effectively saw no product landing page. The sitemap also omitted products and category routes, and there was no Product/Organization structured data. This is the #1 technical SEO gap from the strategy doc.

## What Changes
- Split the product detail route: the existing UI becomes a client island (`ProductDetailClient`, seeded with `initialProduct`), and `products/[id]/page.js` becomes a server component that fetches the product, emits `generateMetadata` (title «قیمت {name} امروز + خرید مستقیم — {siteName}», description, canonical, OG), and injects Product+Offer and BreadcrumbList JSON-LD.
- Add Organization/LocalBusiness JSON-LD once in the root layout.
- Show a price-freshness line («به‌روزرسانی قیمت: …») on the product page.
- Expand `sitemap.js` to include all products and the six product families.
- New server helpers `lib/productsSeo.js`; reusable `components/JsonLd.js`.
- The `/products` list page and its filters are intentionally untouched (query-param filtering stays for internal use).

## Impact
- Affected specs: `product-seo`
- Affected code (frontend, kavehmetal): `app/products/[id]/page.js` (now server), `app/products/[id]/ProductDetailClient.js` (new), `app/lib/productsSeo.js` (new), `app/components/JsonLd.js` (new), `app/layout.js`, `app/sitemap.js`.
- Env: `NEXT_PUBLIC_SITE_URL` must be set on the server for correct canonical/sitemap URLs.
- No backend changes (uses existing `/api/products/<id>/` and `/api/products-summary/`).
