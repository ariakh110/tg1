# 02 — How Search Engines Work

## The pipeline: Crawl → Index → Rank → Serve
1. **Crawl** — Search engines run programs called **robots / crawlers / spiders**. They discover new pages primarily by **following links**. (Each engine has its own bot.)
   - Early web required manual submission; now bots find sites on their own. Adding the site to **Google Search Console** (formerly Google Webmaster Tools) aids discovery.
   - They do not crawl all pages at once; full coverage of a site can take weeks/months. Most sites get some pages crawled daily.
2. **Index** — Crawled content is analyzed (what topic, how well covered) and stored in a massive database called the **index**. Data centers worldwide enable fast retrieval.
3. **Rank** — On a query, the engine searches its index, then in a fraction of a second determines (a) which results are **most relevant** and (b) ranks them by **authority**.
4. **Serve** — Returns ~10 organic results plus ads.

## Links = votes
- A link from site A → site B is a **vote / endorsement** of B's usefulness.
- Links help Google decide which relevant pages to rank first.
- **Links are not equal.** A site with few powerful links can outrank one with many weak links. One link can be worth a million times another.
- Links from low-value / low-integrity sites may carry **no value at all**.
- Why links still matter even as content understanding improves: implementing a link requires owning a site that meets engine criteria, and a link invites users to *leave* your site — so it's a meaningful signal. Google periodically "turns the dial back up" on links to defend against low-quality AI-generated content.

## Relevance
- A page ranks for terms it is **relevant** to — and its specific relevance also **prevents** it from ranking for unrelated terms (a Star Wars page won't rank for Ford Mustangs).
- Beyond relevance: **comprehensiveness** — how fully you satisfy the query *and* the user's likely follow-on questions.

## Site structure & crawlability
- You must structure the site so pages are **discoverable**. It is possible to accidentally build a site where pages can't be crawled/indexed.
- Many things can **block** crawling/indexing (robots.txt, noindex, poor architecture). A clear hierarchy is essential for both users and bots.
- **Cloaking** (showing different content to bots vs. users) → penalties. User experience comes first, but the site must be valuable from both perspectives.

## The rise of AI (as taught in the course, ~2023)
- Generative AI (ChatGPT, Gemini) enables a flood of low-cost content that is often just regurgitation.
- Google defends search quality by (a) favoring content showing **real human experience**, and (b) increasing the weight on **links** and trust signals.
- → Implication for agents: prioritize first-hand experience, originality, and authority. (See `../knowledge-base-2026/` for how this evolved into AI Overviews, GEO/AEO, and the "experience" E in E-E-A-T.)
