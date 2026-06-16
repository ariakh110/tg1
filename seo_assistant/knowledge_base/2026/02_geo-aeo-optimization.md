# 02 — GEO / AEO: Optimizing to be cited by AI engines

Two overlapping new disciplines extend SEO into the AI-answer era:
- **GEO — Generative Engine Optimization** (a.k.a. **LLMO**, LLM Optimization): getting your content understood, trusted, and **cited** by LLMs (ChatGPT, Gemini, Perplexity, Claude) when they generate answers.
- **AEO — Answer Engine Optimization**: optimizing content to be the cited answer in AI search/answer engines.

In practice GEO/AEO overlap heavily; treat them as "optimize to be the source an AI quotes."

## Why it matters
When someone asks an AI engine, it **synthesizes** an answer from multiple sources and **cites the most authoritative** ones. If you're not citable, you're invisible in that channel — even if you rank on classic Google.

## How to get cited — checklist
1. **Self-contained answer at the top of each page.** LLMs extract these as canonical passages. Make the answer explicit and include at least one **specific statistic or named entity**. (This is the "answer-first" / inverted-pyramid pattern.)
2. **Structured, extractable formatting.** **Bullet lists and comparison tables** are the formats AI engines cite most. Use clear H2/H3 question-style headings, concise definitions, FAQs.
3. **Structured data / schema (JSON-LD).** Baseline requirement. The compounding signal is **entity reinforcement**: your `Organization` schema points to founders/authors, and AI engines follow that entity graph. Use Article, FAQPage, Product, Organization, Person, HowTo, etc.
4. **`llms.txt` at the site root.** An emerging standard: a machine-readable file telling AI crawlers what content exists and how to interpret it. Maintain it accurate and complete.
5. **Allow the AI bots in `robots.txt`.** If blocked, you're invisible to that engine. Common bots to allow: **GPTBot, OAI-SearchBot** (OpenAI), **PerplexityBot**, **ClaudeBot** (Anthropic), **Applebot**, **Google-Extended** (Gemini/Vertex). (Decide deliberately — allowing = citable; blocking = protect content but lose AI visibility.)
6. **Freshness.** Perplexity (and others) weight **recency** heavily — an article updated recently beats an identical one frozen years ago. Keep content dated/updated.
7. **Authority & off-site presence.** LLMs lean on widely-corroborated, reputable sources: earn mentions/citations, maintain consistent brand info, get represented on third-party authoritative sites, Wikipedia/Wikidata, and reviews. (This is E-E-A-T applied to AI — see `03_eeat-2026-experience.md`.)
8. **Originality & experience.** Provide first-hand data, studies, examples, and expert quotes the model can't generate itself. Data-driven research (the course's "anchor content") is prime citation bait.
9. **Consistency across the web** — same facts/entity details everywhere so the model's corroboration is unambiguous.

## Relationship to classic SEO
GEO/AEO is **additive**, not a replacement. The same content that earns E-E-A-T, links, and rankings is what gets cited — you're now also making it **machine-extractable** and **entity-anchored**, and ensuring AI bots can access it. Keep doing on-page, technical, content, and link work; layer GEO/AEO on top.
