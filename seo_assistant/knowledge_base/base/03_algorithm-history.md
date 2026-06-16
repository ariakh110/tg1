# 03 — Algorithm History & Major Updates

> Knowing past updates lets you predict Google's direction. **Two themes** run through all of them: (1) a more **user-friendly** web, (2) **better understanding of user intent**.

## Algorithm basics
- Algorithms determine a site's quality, theme, and which queries it should appear for, and where it ranks.
- Google uses **200+** ranking signals; **500+** updates/year; most are unannounced and vague.
- Track turbulence with tools like **MozCast** (ranking-fluctuation "weather") and Moz's annual ranking-factors report.
- Be **proactive**, not reactive: optimize for the user and follow best practices so you survive updates.

## PageRank (the original link algorithm)
- Created by Larry Page. Each page gets a value from the number + quality of inbound links; value ("link juice") flows out through its links, split among them.
- Scored 0–10 (Toolbar PageRank); exponential to climb. Last public update **2013** — now defunct as a public metric.
- The concept lives on as **"authority."** Tool vendors approximate it: Moz **Domain Authority / Page Authority**, Ahrefs, Majestic, SEMrush. Scores 0–100 on a **logarithmic** scale (a DA 60 link ≈ 10× a DA 50 link).
- Note: links with **nofollow** pass no PageRank (all social media links are nofollow/UGC).

## Panda (2011) — content quality
- Hit ~**12%** of results. A recurring **filter** (re-runs; recovery possible after fixes).
- Targets: **duplicate content** (cross-site or internal), **thin content**, machine-generated/spun content, doorway pages, squeeze pages, excessive ads, low-quality guest posts, scraped content.
- Internal duplicates **cannibalize** each other. First publisher generally gets credit for content.
- Fix: view the site as a *user* would; remove/improve thin pages; ensure unique, valuable content and intuitive navigation.

## Penguin (2012) — link spam
- Targets manipulative link building: link networks, reciprocal/traded links, comment spam, **aggressive exact-match anchor text**, paid links, links from low-quality/irrelevant sites, directory spam, free-widget/template footer links, forum-signature links.
- A **filter** (re-runs). Spawned fear of **negative SEO** → Google's **Disavow tool** (in Search Console). Only disavow if actually penalized / links are clearly toxic; try manual removal first.

## Hummingbird (2013) + RankBrain — semantic search
- Better understanding of meaning via **semantic indexing**: synonyms and related words determine topical relevance (a baseball page → "home run," "bat," "catch").
- Foundation for BERT. Shifts SEO from keyword density toward **topic association**.

## Mobilegeddon (2015) + Mobile-first (2018)
- Mobile-friendliness became a ranking signal; mobile version indexed over desktop. Majority of searches are mobile.

## BERT (late 2019–early 2020) — natural language
- "Bidirectional Encoder Representations from Transformers." Affected ~**1 in 10** queries at launch.
- Reads sentences **forward and backward** for full context; now uses **stop words** (to, with, by, at, on, **no**) it previously ignored. Improves sentiment understanding.
- You **don't "optimize for BERT"** directly. Instead: write clearly for humans, in the audience's voice/level; state plainly what you solve; include relevant detail.

## E-A-T & YMYL (Medic update, late 2018)
- **YMYL = Your Money or Your Life**: any page that can affect health, happiness, safety, or finances. Broad — advice counts even without a transaction.
- **E-A-T = Expertise, Authoritativeness, Trustworthiness** (Google later added a second **E = Experience** → see 2026 layer).
  - **Expertise:** author/site are subject experts → high-quality content, clear About page, author bio pages with credentials.
  - **Authoritativeness:** recognized by others → links/citations from press, speaking gigs, social discussion, branded search volume, Wikipedia mentions.
  - **Trustworthiness:** on-site (accurate contact info, return policy, payment/shipping terms, T&Cs, **HTTPS**) + external (brand sentiment, reviews on Trustpilot/Yelp/TripAdvisor, BBB registration in US).
- Backed by human **Quality Raters** using the **Search Quality Rater Guidelines**.

## Core Web Vitals (announced July 2020, rolled out 2021) — UX metrics
- "Real-world experience metrics." A ranking factor (not *the* factor — confirmed by Gary Illyes).
- Measures page load, stability, security, intrusive pop-ups. Impacts mobile + desktop rankings and eligibility for **Top Stories** (AMP no longer required; must meet a minimum CWV score).
- Google data: can reduce site abandonment by up to **24%**.
- Buckets: **Good / Needs Improvement / Poor**. Measure via **Search Console**, **Lighthouse**, PageSpeed Insights.
- (Original metrics: LCP, **FID**, CLS. FID was replaced by **INP** in March 2024 — see 2026 layer.)

## Other notable updates
- **Caffeine** — speed / faster indexing infrastructure.
- **Personalized search** — location, history.
- **Payday Loan** update — targeted notoriously spammy verticals.
- **QDF (Query Deserves Freshness)** — trending topics favor fresh content.
- Entity association / entity matching — matching queries to specific people/things (brand signals).
