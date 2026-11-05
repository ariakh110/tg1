# Final handoff — angle/channel catalog seed

Date2026-11-05; task angle-channel-catalog-seed. User approved described integration
with «بله», delegated workspace selection. Existing dev-ariakhayer retained; no
merge/push, live import, deployment, provider action or Unity change. Frontend's
unrelated dirty handoff/doc files preserved. Do not interpret local completion as
authority to deploy or publish.

## Deliverable

149 native products:84 angles/65 channels;8 inactive categories;18 family options;
65 nominal sizes. Products inactive/noindex/inquiry; no offers/prices/media or
invented measurements/weight/certification.3 combinations quarantined;42 unknown
manufacturers need review. Source snapshot collected2026-11-05, not continually
updated. Matrix remains sheet/coil-only; use this independent importer instead.

Runtime commits: f5eee1f, e68c255, a10fc4e. Plan:
docs/superpowers/plans/2026-11-05-farda-sections-seed.md. Authoritative requirement:
openspec/changes/add-angle-channel-catalog-seed/specs/catalog-seeding/spec.md.
Historical BMAD/preparation receipts are preserved; current implementation/report
supersedes their pending-approval status wording without mutating hashed artifacts.

## Files and operation

- products/catalog_seed.py, products/data/farda_sections_v1.json;
  products/management/commands/seed_farda_sections.py.
- ops/manual_deploy/seed_farda_sections.sh and one call in update.sh after migrate.
- products/test_catalog_seed.py, products/test_catalog_seed_release.py and native
  read-query/option-validator compatibility fixes in api_views/views/serializers.
- Reports: farda-seed-implementation.md (Persian operator steps),
  farda-seed-spec-review.md, farda-seed-quality-review.md, farda-seed-ledger.md,
  farda-seed-self-evaluation.md under docs/engineering/reports/.

`python manage.py seed_farda_sections --dry-run` is read-only. An authorized next
backend update runs preview then explicit apply with actor release:update.sh;
hash mismatch/conflicts stop it. SHA256 of pinned asset:
e9d903b8fe338bee4d72767311e9e236daf73f949280449af9fb750f19affa57.
Never erase receipts to replay: batch protects edited/deleted rows; incomplete
receipts demand manual review. Matching existing products are skipped untouched.

## Evidence and review

Final full Django suite501/501 passed36.177s on SQLite settings_test with temporary
MEDIA_ROOT. Focused53 pass. Before-review full495 passed twice; six new regressions
failed before one fix pass, then green. Django check, no missing migration, strict
OpenSpec,8 offline tests,13 frontend SEO tests and native SEO model on149 rows pass.
Archive preserves data bytes; Bash/helper tests execute fake interpreter boundary,
not a real update. The expected injected matrix RuntimeError log is a passing
rollback test, not an unreported production failure. Disposable upload fixtures
from earlier tests were verified against exact known test bytes then removed;
no user media was removed. No Next build/browser/live SSR/PG race test claimed.

Independent read-only reviewer gpt-6-astra reviewed552ebe0..e68c255: no Critical;
three Important found, all corrected/tested in a10fc4e. No second reviewer. One
Minor deferred: independent failure injection during spec save and final batch
audit save; shared transaction and second-product rollback are already tested.
Full rulings/costs and evidence are in quality review/ledger, not silently dropped.

## Next authorized action

No local imports ran against development DB: apply/replay only in test DB. Before
server use, obtain deployment authorization, backup destination, review preview
conflicts and stage with actual PostgreSQL/environment. After successful update,
review metadata/unknown facts, activate selected categories/products and explicitly
change noindex only after technical/editorial verification. Add real seller/price
through existing management workflow; never copy source price/stock. Preserve
this branch until the owner chooses integration; no automatic publication.
