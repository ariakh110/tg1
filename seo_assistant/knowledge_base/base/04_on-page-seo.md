# 04 — On-Page SEO

On-page = optimizing elements within a page/its code: content, keyword choice, metadata, headings, URLs. **The single most important on-page element is the page's content**; the title tag is the most important *tag*.

## Title tag
- Shows in search results, the browser tab, and the source code (`<title>...</title>`).
- **Best practices:**
  - Length: **≤ 60 characters**; aim for **~55** to be safe. Longer text gets cut off in results → poor UX, lower CTR.
  - Put the **most important keyword(s) at the front**; Google weights the start more, and users read it first.
  - Put the **brand name at the end**, separated by a **pipe `|`**. Exception: very well-known brands may lead with brand for CTR.
  - Focus on **no more than two keywords** per title (tight focus = more relevant, easier to rank).
  - If using multiple keywords, separate with **hyphens** (e.g., `Winemaking Course - Learn Winemaking | UC Davis Extension`).
  - Avoid special characters (stick to alphanumeric); some engines render them poorly.
  - Each page needs a **unique** title.

## Meta description
- The text block under the title/URL in results. **Not seen on the page**; hidden in source (`<meta name="description" content="...">`).
- **Keywords here do NOT help ranking** — but it strongly influences **CTR** (matched query words appear **bold**).
- **Best practices:**
  - Length: keep **under 160 characters**; aim for **150–160**. Too long → cut off or rewritten by Google; too short → weaker CTR.
  - Accurately describe the page, naturally include likely query words (so they bold).
  - Include a **call to action** ("Learn more," "Read our article," "Download here," "Watch our video") — proven to lift CTR.
  - Avoid quotation marks / special characters (quotes can truncate the description).
  - For broad/blog pages it's OK to let Google auto-generate it; for static/article pages, write your own.
  - Also used by social networks as the share description → another reason to optimize.

## Meta keywords
- **Obsolete / ignored by Google** (abused historically). Do not spend effort here.

## URL optimization
- A URL describes the page to users + engines. Should be **relevant, keyword-bearing, and short**.
- Keywords in URL still help a little (less than before, post over-optimization). They also act as **anchor text** when others link using the bare URL.
- Use **subdirectories/subfolders** to categorize (`/areas-of-study/winemaking/`); keyword subfolders can appear bolded in results.
- **Avoid parameters** (e.g., session IDs) — they bloat URLs and create **duplicate content** (same content, changing URL).
- **Don't change URLs just for SEO.** A ranking page loses history/authority when its URL changes. If you must change: use a **301 (permanent) redirect**; expect time for Google to re-index.
- Best to **optimize the URL from the start** (new pages / redesigns). Order of preference: optimize the URL when creating it; otherwise often leave existing URLs alone and improve other on-page elements.

## Heading tags
- **H1** = primary heading (most important for SEO); **H2** = secondary (somewhat important). **H3+** are essentially **not used** by engines for ranking — used for structure/UX.
- **Rules:**
  - **One H1 per page.** Don't wrap the site name or menus in H1/H2 (creates duplicate/irrelevant signals).
  - Incorporate keywords into H1/H2 **only if natural** and reinforcing the title/theme; otherwise leave them out.
  - Don't stuff multiple heading tags just to add keywords (looks spammy).
- Inspect with View Source / "Inspect element" / MozBar (Page Elements).

## Content (on-page)
- **Quality, unique content** around the page's topic/theme is essential — without it a page can't rank well.
- Include the **focus keyword + related/semantic keywords**, fitting **naturally** (read it aloud; get a second opinion). Forced/repeated keywords → **over-optimization penalty**.
- Use **synonyms** and **topical associations** (a movie page: film, cinema, theater, popcorn) — supports semantic relevance and captures long-tail.
- **Avoid duplicate content** — across sites and **within** your own site (don't copy a page and swap a city/location name). Duplicates cannibalize each other. First publisher usually gets credit; quoting is fine if surrounded by your own content + a link to the source.
- Organize content within **subdirectories** by topic (e.g., movie reviews by genre).
- Add **value beyond text**: images, video, downloadables, links to useful resources (internal and external). A giant text block, however well-written, is less useful than one with mixed media.
- **Internal linking** with descriptive **anchor text** (not "click here") to related pages — helps users + crawl discovery + topical authority.
- Match the **reading level** to the audience.
- Always include a **call to action** to drive conversion/engagement.

### Quick-win on-page fixes (for new engagements)
- Ensure Search Console + Analytics installed; XML sitemap submitted; robots.txt present with appropriate blocks.
- Trim keyword-stuffed title tags; add text to thin homepage/key pages; add **alt text** to images (accessibility + UX even without keywords); internal-link to important pages.
