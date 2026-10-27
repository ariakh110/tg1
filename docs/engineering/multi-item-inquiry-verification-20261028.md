# Multi-item inquiry: implementation, review and verification

Contract: multi-item-inquiry-design-20261028.md; OpenSpec add-multi-item-purchase-inquiry. Owner confirmed storefront inquiry/multiple purchase items, not admin product creation.

## Spec compliance

Active catalog categories/ancestors populate options; code-time server validation snapshots category names. Nested1–50 items preserve specification <=200, positive two-decimal quantity and explicit kg/ton/branch/sheet/piece/meter unit. Old product/size/kg requests and old stored challenges still work. Whole nested payload is canonicalized and hashed; changes under same ID reject. One verified request has one inquiry, requested_items JSON, customer/lead and opportunity, one reference. Repeated verify returns the same reference; no catalog products written.

Migration assistant0006 adds requested_items with [] for legacy records, read-only in admin API. Full items render inside admin inquiry details. Actual CRM structured field is CrmOpportunity.metadata.requested_items; design's phrase source payload refers to this field, not a new property named source_payload. Raw readable list is also retained; bounded need_details remains2,000 chars, metadata preserves all50.

UX: compact RTL list/contact/OTP progression, add/copy/delete, atomic TSV import with numbered errors, category context/defaults and per-kind hints, one contact for all rows, review summary, persistent action footer, loading/error/retry states, close/back preservation and native modal keyboard controls. Personal information remains in component memory, not localStorage. No unit conversion or cross-unit total.

## Independent quality review and single fix pass

Fresh read-only reviewer multi_inquiry_review (gpt-6-astra) found two Important: category changes reset chosen units; CRM projection only after commit could fail despite success reference. Both fixed with regressions: unit preservation respects entered quantity/explicit selection; new multi-item flow synchronously invokes idempotent CRM sync inside verification transaction. Injected CRM failure returns redacted503, rolls back inquiry/customer/opportunity/challenge link and the same valid OTP then succeeds exactly once. Existing postcommit projection remains idempotent for later updates/legacy.

Two findings labelled Minor by reviewer were treated as acceptance issues because keyboard workflow and quantity interpretation affect fast, accurate entry: back/reset focus now lands on list heading (browser assertion first failed on prior build, then passed); TSV explains decimal/thousands convention, rejects grouped numbers with leadingzero such as0,001 instead of silently converting to1 (unit regression RED then GREEN). No deferred findings. No second review dispatched after fixes.

Decisions: code-time category snapshot remains valid if taxonomy is later deactivated; this is a request for sales review, not a stock/price reservation. Full list belongs in existing metadata. Retain current non-main checkouts and scoped staging to preserve unrelated docs. Cost of these choices: sales may receive a now-hidden requested category; consumers must use actual metadata schema; unscoped staging would mix unrelated edits and is excluded.

## Actual checks

- New backend tests initially failed (legacy-only400, missing options/model field), then passed. Review regression initially returned201 despite CRM failure, then503 with full rollback after fix.
- `.venv/Scripts/python.exe manage.py test assistant customers messaging products accounts.test_admin_sections --settings=tg1.settings_test --noinput`: **261 passed**,11.726s after final fixes. Existing matrix late-error test intentionally prints traceback while proving rollback.
- Wider first run exposed an unrelated clock-dependent CRM test: now+2h crossed midnight, yielding today0/upcoming2. Freeze that test's clock at10:00 UTC (test-only; no production follow-up logic changes). Full rerun260 and final261 both passed.
- Django check clean; makemigrations --check --dry-run clean; migration0006 applied in isolated test DB. No production migration executed.
- `node --test tests/*.test.mjs`: **64 passed** after final fixes.
- ESLint new widget/editor/helper/API/unit/browser files: exit0. AssistantPanel baseline/current each have same3 existing react-hooks/set-state-in-effect errors, no new rule failures. No whole-repository lint claim.
- `npm.cmd run build`: production build exit0 after final fixes (existing middleware deprecation warning).
- Local production localhost3000 + tests/purchaseInquiry.browser.cjs: multi-family add/copy/delete, atomic failed/successful paste,50-row import, one contact, immutable retries/new request after edit, malformed code response, incorrect/correct OTP, cooldown, close/reopen/focus trap/back focus, admin full list. Three mock code calls (one malformed response retry, one edited request), two mock verify calls (wrong then valid), no page errors/unexpected writes. RTL desktop/mobile screenshots inspected.
- git diff --check clean. OpenSpec CLI not on PATH; delta reviewed manually, no CLI validation claim.

Evidence Windows TEMP: multi-inquiry-{backend-final,node-final,build-final,browser-final}.log; review RED logs; kavehmetal-multi-inquiry-production/{checks.json,desktop-list.png,desktop-contact.png,mobile-list.png}. All provider/API writes mocked, no real SMS. No live deployment, real provider delivery, production DB/PostgreSQL concurrency or quota-store outage beyond mocked tests verified.
