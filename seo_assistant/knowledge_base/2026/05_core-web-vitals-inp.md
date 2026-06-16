# 05 — Core Web Vitals Update: INP replaces FID (March 2024)

## What changed vs. the course
The course covers Core Web Vitals with the original triad **LCP / FID / CLS**. As of **March 12, 2024**, **FID (First Input Delay) was replaced by INP (Interaction to Next Paint)**.

## The current Core Web Vitals (2024+)
| Metric | Measures | "Good" threshold (75th percentile) |
|--------|----------|-----------------------------------|
| **LCP** (Largest Contentful Paint) | Loading | ≤ **2.5 s** |
| **INP** (Interaction to Next Paint) | **Responsiveness** | ≤ **200 ms** |
| **CLS** (Cumulative Layout Shift) | Visual stability | ≤ **0.1** |

### INP detail
- **INP measures responsiveness across the ENTIRE visit** — every click/tap/keypress — and reports a single representative value. (FID only measured the delay before the *first* interaction's handler began.)
- Thresholds: **≤ 200 ms = Good**, **200–500 ms = Needs Improvement**, **> 500 ms = Poor**.
- The FID→INP switch dropped mobile CWV pass rates by ~5 percentage points (HTTP Archive 2025 Web Almanac) — INP is harder to pass.

## Ranking role (unchanged in spirit)
- CWV/INP is part of **page experience signals** and acts as a **tiebreaker**, not a primary factor. **Content relevance still wins.** Poor INP can disadvantage you against equally-good competitors. (Consistent with the course: CWV is "a ranking factor, not *the* ranking factor.")

## How to improve INP
- Reduce/break up long JavaScript tasks; defer non-critical JS.
- Minimize main-thread work; optimize event handlers.
- Use `requestIdleCallback`, code-splitting, web workers for heavy work.
- Reduce third-party script impact; avoid large layout/style recalculations on interaction.

## Tools (same as course + current)
Google **Search Console** (Core Web Vitals report), **PageSpeed Insights**, **Lighthouse**, Chrome **CrUX** field data, web-vitals JS library.
