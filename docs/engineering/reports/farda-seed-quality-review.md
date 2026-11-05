# Independent quality/security review — angle/channel seed

2026-11-05. One read-only independent reviewer (`gpt-6-astra`, xhigh), required by
executing-plans, reviewed whole feature range552ebe0..e68c255 against the accepted
OpenSpec/BMAD contract, plan, review focus and ledger. No reviewer writes to code,
Git or real DB. Reviewer independently ran8 offline tests, Bash syntax and diff
whitespace checks. Full Django/Node results are coordinator evidence, not claimed
as independently re-run by reviewer. Verdict before fixes: **With fixes**.

Strengths: byte-pinned approved/offline data, hash checked before writes, atomic
data+audit, durable replay receipt preserving edits/deletes, correct release
preview/apply failure propagation, no prices/offers/media or invented weight.
No Critical finding.

## Important findings accepted for one TDD fix pass

1. Public summary list/detail and generic specifications/spec-values still exposed
   inactive products. Scope the relevant read querysets to active products for
   non-admin while preserving admin preview and existing write policies.
2. Importer option identity was family-scoped but native editing duplicate checks
   were not: seeded angle/5SP collides with existing billet/5SP. Align family scope
   for unparented options with the NULL-parent database constraint semantics, keep
   non-null-parent constraint checks, and use case-insensitive matching consistently
   in importer and validator so uppercase factory codes are reused or conflict.
3. Nominal '6.50' and '6.5' compared as raw strings and could duplicate a channel.
   Canonicalize valid numeric nominal values for identity only, never rewrite stored
   values or infer height. Two equivalent existing products must conflict atomically.

Regression tests and final results are recorded in the implementation report and
final handoff. No second review is dispatched: one test-first fix pass and full
suite verification are required before claiming these resolved.

All six new regression methods failed before the changes; the corrected focused
suite passes53 tests. The existing anonymous summary-index test was updated to
expect exclusion publicly and to retain its inactive/noindex assertion through
authenticated admin preview. This is an intentional publication-policy change,
not deletion of the old indexing check. Full-suite result follows in handoff.

## Deferred minor

Add separate injected failures during specification save and final batch-audit
save. Existing test injects failure at the second Product.save and checks complete
rollback; actual implementation keeps all three locations in the same transaction.
Reviewer graded this extra location coverage Minor; coordinator accepts that grade
and defers it rather than changing additional behavior in the fix pass.

## Declined-to-judge rulings by coordinator

- Current source accuracy and engineering certification of angle units: preserve
  approved snapshot and explicit accepted mapping; no fresh source crawl or claim
  of engineering certification. Cost if wrong: correct factual records before
  publication after human technical review.
- Live PostgreSQL concurrency, destination conflicts and server configuration:
  preserve local/static evidence only; require destination preview and backup on
  an authorized run. Cost if wrong: release can stop; this is not proof of live
  environment readiness, parallel-operator safety or live import success.
- Matrix expansion and a general Offer/media authorization audit: remain outside
  this seed. Related summary/spec/value exposure enters the fix pass. Cost if wrong:
  the sheet matrix remains limited and unrelated legacy Offer/media weaknesses
  may remain; no imported offers/media add to those surfaces.

Other coordinator ruling: restrict inactive primary product detail for non-admin
to honor unpublished defaults. Compatibility cost: public consumers previously
using inactive product details now receive404, including related read surfaces
after the fix pass; admin preview remains. No endpoint/payload/schema added.

Final gate after the one fix pass: all3 Important findings resolved with observed
RED→GREEN regressions; 53 focused tests and501/501 full tests pass (36.177s). The
coordinator's final local quality/security gate is PASS, not a claim the independent
reviewer re-reviewed fixes. Runtime commit a10fc4e. One Minor remains deferred above.

Additional ruling: align the prior summary-index regression with that same public
policy and keep the indexing assertion for admin. Cost if wrong: clients formerly
depending on anonymous draft summaries break, the already disclosed compatibility
cost; summary payload fields themselves do not change.
