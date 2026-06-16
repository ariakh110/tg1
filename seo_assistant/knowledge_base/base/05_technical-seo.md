# 05 — Technical SEO

Technical SEO lays the **structural foundation** so engines can discover, crawl, and understand content. You don't need to code, but you must spot issues. Typical order: **technical review → content/keywords → off-page**.

## Sitemaps
- **XML sitemap** — for search-engine robots. Lists URLs + metadata (last-modified, change frequency, priority). Especially valuable for **new sites** not yet discovered. Submit via **Google Search Console** / **Bing Webmaster Tools**.
- **HTML sitemap** — for users; a page of links to important pages.
- Ideally have **both**. Create XML sitemaps with crawlers like **Screaming Frog** (free up to **500 URLs**) or XML-sitemaps.com (also ~500 free).

## robots.txt
- File telling crawlers which areas **not** to crawl. Ensure it exists and blocks only appropriate areas.
- When auditing: if missing, recommend creating one (and justify which pages to block); if present, compare to the live site and recommend changes with reasons.
- Quick-win: confirm robots.txt is uploaded with appropriate blocks; confirm XML sitemap is referenced and accessible.

## HTTP status / error codes
- **200** OK — page loaded successfully.
- **404** Not Found — page removed/doesn't exist; engines drop it from the index. Normal in moderation.
  - **Soft 404** = page is gone but still returns **200** (e.g., "product no longer available"). Bad: engines see live, thin, duplicate pages. Common on e-commerce / real-estate sites. Detect via **Search Console**.
- **500** Server Error — generic; often temporary/self-resolving. If persistent, check server logs.
- **503** Service Unavailable — correct code for planned downtime/maintenance/overload; tells engines "temporary, revisit later." **Always return 503 (not 500) when taking a server down.**
- Code families: **4xx** = client/page errors; **5xx** = server errors.

## Redirects
- **301 — Permanent redirect** (preferred for SEO). Tells engines the page permanently moved; passes most authority/"link juice" to the new page. Note ~**5%** authority loss per redirect.
- **302 — Temporary redirect** (and newer **307**). Passes little/no authority; keeps old page in index. Use only for genuinely temporary cases (e.g., maintenance).
- **Meta refresh** — page-level (no HTTP status), slow, visible to users ("if not redirected in 5 seconds…"), gives unclear signals. **Not recommended.**
- **Rules:**
  - Default to **301** in almost all cases.
  - **Avoid redirect chains** (A→B→C). Point A→C and B→C directly to preserve authority.
  - Redirect an old page to the **most semantically similar** page. Order of preference: specific matching page → category page → homepage (homepage only as last resort).
  - After redirecting, **update internal links** to point at the new URL directly (external links still rely on the redirect).

## Crawlability & analysis
- Use a crawler (Screaming Frog) to find pages not visible in manual review, duplicate metadata, missing headings, error pages, content type/status codes.
- Check duplicate content (Copyscape, or quote a snippet in Google with quotes).
- Check the backlink profile for spam/over-optimized anchors → signals past bad SEO / possible penalties.
- Ensure a **clear hierarchy** and that the site is **accessible to both users and bots** (no cloaking).
