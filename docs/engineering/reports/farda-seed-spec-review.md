# Spec compliance review — angle/channel seed

2026-11-05. Reviewed by implementation coordinator; separate independent quality
review is recorded in farda-seed-quality-review.md when returned. This is not a
claim that the same-author compliance pass is independent.

Requirements: OpenSpec add-angle-channel-catalog-seed/catalog-seeding; approved
BMAD SPEC-angle-channel-catalog-seed. Owner's «بله» authorizes the described local
implementation after preparation. Workflow receipts retain the historical design;
this implementation report supersedes its pending-approval status text only.

| Capability | Evidence | Result |
| --- | --- | --- |
| CAP-1 source trace | pinned package equals reviewed candidate; offline compiler tests retain 467 observations as 461 product provenance + 6 quarantined observations | pass |
| CAP-2 native catalog | isolated DB creates 149 Product/Specification, 8 categories, 18 family-scoped options and 65 nominal SpecificationValue; unknown dimensions/weight remain null | pass |
| CAP-3 owned SEO/unpublished | stored Persian name/H1/meta/title/FAQ/table, internal slug; native frontend SEO model checks all 149, no fresh tier; inactive/noindex/inquiry, public detail404 and admin detail200 | pass |
| CAP-4 safe next-update seed | real DB preview/apply/replay/conflict/rollback; required actor, byte hash; Bash helper preview-before-apply and exit propagation; updater call after migrate, committed archive hash | pass |

Constraints: no Offer/PricingTier/media, no source prices/stock or networking in
seed, no schema changes, no sheet-matrix extension, no mutation of existing
catalog records. All495 backend tests passed twice (31.968s and30.307s), including
42 seed+matrix/identity and5 shell/archive checks. 8 offline source tests and13
frontend SEO tests pass. Django check/migration consistency/OpenSpec strict pass.

Final independent review found3 Important issues; one TDD fix pass added6 real DB
regressions and resolved all3 (public related read surfaces, option scope/case and
numeric nominal identity). Final53 focused and501 full tests pass (36.177s); Django
check, migration consistency and strict OpenSpec validation were repeated cleanly.
Review details/rulings/deferred minor: farda-seed-quality-review.md. Runtime commit
a10fc4e follows f5eee1f/e68c255. No second review or production execution claimed.

SEO skill final check read the actual app/products/[id]/page.js: canonical uses
the site's configured SITE_URL and product.slug; Product/Breadcrumb/FAQ schemas
consume owned fields. Offer schema is conditional on a fresh positive price;
native model returns null freshTier for all seed rows. Category roots are fetched
dynamically in productsSeo.js; unpublished roots are not listed publicly. This
is source/model verification, not a deployed HTTP/SSR/browser test. Some generated
titles are long because they preserve distinguishing product facts; editorial
length tuning should happen before publication, not mutate the pinned package.

Safety adjustment: inactive public retrieve was an existing leak. Restricting it
to active products (unless admin) is necessary for approved unpublished defaults;
no new endpoint or payload shape. Existing authorized admin preview passes.

Boundaries: no real import, provider action, network scrape at deployment, release,
merge or push performed. No Next build/browser/Core Web Vitals measurement, Google
rank assertion or PostgreSQL concurrency integration test. Those are not implied
by local SQLite/API/helper success. The shared workflow receipt records this
evidence but does not independently prove test quality or authorization identity.
