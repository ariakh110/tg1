# 08 — Off-Page SEO & Link Building

Off-page = actions outside your site to support on-site/technical SEO: **links** + **brand recognition/visibility** (social, mentions). Closely resembles PR.

## How links are valued
- Inherited from **PageRank**: value flows through links, split among outgoing links; modified heavily today + supplemented by new algorithms.
- PageRank is assigned to **pages, not domains** (Google says it doesn't use a site-level PageRank, despite vendor "domain authority" metrics).
- Vendor authority metrics (Moz DA/PA, Ahrefs, Majestic, SEMrush) run **0–100 on a logarithmic scale**: a DA-60 link ≈ **10×** a DA-50 link; a DA-70 link ≈ 100× DA-50 ≈ 100,000× DA-20. → prefer fewer high-authority links over many weak ones (at equal relevance).
- **nofollow** links pass **no PageRank** (all social-media user links are nofollow/UGC).
- Two extra factors on every link:
  - **Relevance** — a link from Car & Driver to a Mustang page >> a link from a weather site. Build **topical authority** in your market.
  - **Editorial integrity** of the linking site — link-sellers / poor-quality sites may have links **entirely discounted**.

## Link attribute types (Sept 2019)
- **nofollow** — don't pass authority.
- **sponsored** — paid/sponsored links.
- **ugc** — user-generated content (comments, social, forums).

## What Google wants: editorially-given citations
Links should be **valid citations** — given because the linker genuinely believes the page is valuable (like academic citations; nothing paid).

**Rules of thumb (Matt Cutts / Eric Enge):**
- Would you want the link **if Google didn't exist**? If no → no value.
- Would you proudly show it to a prospective customer, or be embarrassed?
- Did the giver mean it as a **genuine endorsement**?
- **If you have to argue it's a good link, it isn't.**

**You can't:**
- **Vote for yourself** — self-placed links in comments/social/forums/profiles are ignored.
- **Buy votes** — paid links aren't editorially given.
- **Trade votes** — mass reciprocal/link-swap schemes (limited, highly-relevant swaps you'd make anyway are OK).
- **Steal votes** — injecting links via hacking (obviously prohibited).
- Remember: a link **invites users to leave your site** — people only do that when the destination is genuinely valuable.

## Link tactics — DOs and DON'Ts
**Avoid (waste time / no value / risky):**
- **Press releases for links** — all wire links are nofollow. (Press releases are still fine for *visibility*, not SEO links.)
- **Infographics/widgets** purely for embedded links — only use if accurate, relevant, high-quality, and the publisher knows they're linking to you.
- **Comment/forum/profile-signature spam** — nofollow/UGC, no value.
- **Link exchanges, badges, advertorials** (commercial links with no editorial value).
- **Links from countries where you don't do business.**

**OK / good (done right):**
- **Content syndication** — allow reputable sites to republish your content **with attribution**. Best signal: they add **`rel=canonical`** back to your original (eliminates duplicate-content concern + passes value). Second-best: a link back to your original. Worst: `noindex` on their copy + link (kills dup concern but Google discounts noindexed-page links). Never let them link only to your **homepage**; never push to hundreds of low-quality sites.
- **Multiple links from the same authoritative site are still valuable** (publishing a recurring column in the NYT impresses *more* than one article — engines value content as users do). The "one link per site" cap is a myth.
- **Earn links** via great content, thought leadership (speaking, interviews, cited research, publishing on authoritative sites), and relationships with **the media** (vertical-specific authoritative sites count as much as general ones due to relevance).

## Negative SEO & Disavow
- **Negative SEO** = a competitor builds spammy links at you to trigger a penalty.
- **Disavow tool** (Search Console): only use if actually penalized or links are clearly toxic; try manual removal first; disavow both www and non-www versions. Don't reflexively disavow — some links may be beneficial.

## Measuring links (KPIs)
Track: total links, **referring domains**, new links, lost links, toxic/low-quality links, and **site authority** (use one consistent tool — Moz or SEMrush). Reporting link count alone doesn't show value; pair with authority over time.
