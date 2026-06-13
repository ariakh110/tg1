## 1. Frontend (kavehmetal)
- [x] 1.1 `lib/productsSeo.js`: `getProduct(id)`, `listProductsForSitemap()`, `bestProductPrice()`, `absoluteMedia()`
- [x] 1.2 `components/JsonLd.js`: renderer + `organizationSchema()`
- [x] 1.3 Split detail page: `ProductDetailClient.js` (seed `initialProduct`) + server `page.js` (`generateMetadata` + Product/Offer + BreadcrumbList)
- [x] 1.4 Price-freshness line on the product page
- [x] 1.5 Organization JSON-LD in root layout
- [x] 1.6 `sitemap.js`: products + 6 families
- [x] 1.7 `/products` list + filters left untouched

## 2. Verification
- [x] 2.1 `npx eslint` on changed/new files
- [x] 2.2 `npm run build` — `/products/[id]` builds as ƒ (server-rendered on demand)
- [x] 2.3 `openspec validate add-product-seo-ssr --strict`
- [ ] 2.4 After deploy + `NEXT_PUBLIC_SITE_URL`: Rich Results test on a product URL; product URLs present in sitemap.xml
