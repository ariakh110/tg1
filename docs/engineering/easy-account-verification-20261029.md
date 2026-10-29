# Easy account verification — 2026-10-29

Scope: OpenSpec `simplify-account-inquiries`, LangGraph `easy-account-20261029`; backend design `docs/engineering/easy-account-design-20261029.md`; frontend plan `docs/superpowers/plans/2026-10-29-easy-account.md`.

## Implemented behavior
- JWT-authenticated customers submit up to 50 inquiry items using server-derived own contact, without purchasing OTP. Missing contact is completed inline. Profile contact is account-authenticated, not represented as SMS-verified. Guest OTP protocol remains intact.
- AccountPurchaseSubmission UUID receipt owns the inquiry and makes retries idempotent. Same UUID and goods return original receipt before revalidating later contact/category changes. Different payload or owner is rejected. Receipt, inquiry, CRM and durable manager notice are atomic.
- Own inquiry history is paginated and contains public customer fields only. Old guest inquiries are not linked by phone; deliberate ownership boundary.
- Four primary buyer destinations, mobile bottom navigation, More for secondary tools; role and marketplace visibility retained. Simple request-price home, independent finance error sections, own profile editing and readable status tracking.

## TDD and tests
- Backend new endpoint/name tests initially RED; 22 focused tests GREEN; explicit unavailable-cache copy regression RED then fixed. Final command `.venv/Scripts/python.exe manage.py test accounts core messaging assistant products customers --settings=tg1.settings_test --noinput`: 315 PASS (17.148 s final run). Django check clean; makemigrations --check --dry-run clean.
- `node --test tests/*.test.mjs`: 70 PASS. Changed feature JS and browser test ESLint clean. Production `npm.cmd run build` passed; expected preexisting middleware/proxy deprecation warning.
- Local Chrome with every API/provider call mocked: easyAccount.browser.cjs, purchaseInquiry.browser.cjs, mobileLogin.browser.cjs PASS. Account suite: 0 OTP calls, 2 submissions using 1 UUID/receipt, 0 page errors/unexpected writes. Guest suite: 3 code requests, 2 verification requests; login suite: 2 issues, 2 verifies, 1 profile binding PATCH.
- Desktop 1440 and mobile 390 screenshots inspected: no horizontal overflow, primary actions visible, More dialog Escape restores focus. Payment failure keeps primary actions usable. Driver sees tools without buyer finance fetches.

## Final review and one fix pass
Fresh read-only reviewer `/root/easy_account_final_review` reviewed backend 960badd..115bfae and frontend c33aa19..1b518ad. No Critical/Minor; two Important findings. This is a report, not independent re-execution of author's tests.
1. Cold startup refresh/profile failure became guest. New browser regression failed (missing recovery block), then AuthProvider distinguishes failed account session from genuine guest and remembers a non-personal recovery flag in sessionStorage. Login success/explicit logout clears it. Widget blocks guest OTP in recovery state. Cold refresh failure and cold profile failure now pass.
2. Profile edit navigation lost goods and uncertain UUID. Browser regression failed (inline completion absent), then contact editing moved inside the same dialog. Missing contact is saved there; after server-commit/lost-response, editing contact and retrying retains exact UUID and one receipt. No personal draft is written to browser storage.
Both addressed in one fix pass, suites GREEN. No re-review was requested. Plan deviation: inline contact completion replaces navigation to edit page to preserve request state. General profile page remains accessible from account navigation.

## Practical limits
No production deploy, provider delivery, real SMS or Bale send. Test database is local SQLite; production lock behavior under concurrent load is not proven here. Idempotency is per supplied request UUID; a deliberate new request is a new inquiry. Full page reload loses the in-memory draft; following a failed/uncertain request, check own request history before starting another. Manager notices use the existing durable bell/Bale pipeline; credentials and live timer delivery need operator setup. No new runtime dependency or feature flag.
