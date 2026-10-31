# Bale automation verification — 2026-10-31

User scope: daily administrator-supplied channel text, morning greeting and activated Safir capabilities; explicit answer customer chooses Bale or SMS. OpenSpec add-bale-channel-automation. Design backend docs/engineering/bale-automation-design-20261031.md; frontend plan docs/superpowers/plans/2026-10-31-bale-automation.md. Existing standing engineering delegation applies; no live send/deploy.

## Final checks
- `.venv/Scripts/python.exe manage.py test accounts core messaging assistant products customers --settings=tg1.settings_test --noinput`:329 PASS,14.593sec. Focused original44 OTP/login/inquiry/account,24 first scheduler/market/OTP,27 after fixes PASS.
- Django check clean; makemigrations --check --dry-run no changes. Python compile for new worker/adapter, Git Bash -n updater/timer clean.
- `node --test tests/*.test.mjs`:72 PASS. ESLint all changed JS/helpers/new browser fixtures clean. Production Next build exit0 after fixes; log local TEMP/bale-automation-build-fixed.log. Existing middleware deprecation / node module-format warnings only.
- Mocked local Chrome: baleAutomation.browser.cjs, mobileLogin.browser.cjs, purchaseInquiry.browser.cjs, easyAccount.browser.cjs PASS. New browser records methods [bale,sms,bale], one preview(no save/send), one schedule save and one master settings PATCH; no page errors or unexpected writes. Delayed preview/save response proves controls disabled while pending. Guest and authenticated inquiry behavior and SMS binding regression retained.
- Screenshots desktop1440/mobile390 inspected; no horizontal overflow. Durable copies learner/Bale.Automation.desktop.png and Bale.Automation.mobile.png. API/provider operations fully mocked.

## TDD evidence
Native Safir method/metadata absent and login/guest503 initially RED; then native string OTP, method snapshots/availability, shared cooldown and no-fallback tests GREEN. Scheduler module/API absent RED; then preview/permissions/windows/master/day receipt/edit dedupe/unknown/Google job GREEN. Frontend helper import RED then72nodeGREEN. Lint ref-render access corrected using sentChannel state; all changed lint clean.

## Final fresh review and one fix pass
Reviewer /root/bale_automation_final_review read-only backend15189af..090cc00,frontendca090f3..99b3104. No Critical;3Important and1Minor. No additional reviewer or re-review. Reviewer did inspection and read-only AST snippets, not suite execution.
- Important: shared all-platform prevalidation prevented healthy Bale if Telegram config bad (and inverse). RED test saw0 sends instead1. Fix: publish independently per destination, retain explicit pre-send failed/unknown outcome in new ChannelPostRun.platform_errors. Both directions now send healthy destination exactly once.
- Important: changing site name could expand previously saved template over4000 and abort entire scheduler before receipt. RED test raised ValidationError before later row. Fix: record failed daily unsent template snapshot and continue other schedules; healthy row sends once.
- Important: input edits while save pending overwritten by setForm(old response); stale preview/token edits similarly vulnerable. Delayed browser assertion RED(false vs expected disabled). Fix: disable whole panel fieldset during requests; save and preview pending controls locked, browser GREEN.
- Minor regraded Important by author: summary failed hid late Google unknown while details correct, potentially misleading operator into duplicating a post. RED expectedunknown gotfailed. Fix: recompute all-destination summary regardless earlier aggregate state, prioritize unknown and inspection wording. No automatic retry added.
All covering regressions GREEN plus full suite/build; no deferred minors remain.

## Review boundaries / explicit rulings
1. Actual Safir enablement accepted from owner; native OTP delivery, credentials, credit, bot channel permissions, provider limits not live tested.
2. Unique date constraint/lock order reviewed; SQLite tests do not prove production multiworker locking. Timer/environment/migrations/timezone production not executed.
3. A reserved send or queued Google job is already started; disabling blocks new reservations, not recall/cancel (cost: old queued job may still deliver).
4. Existing late Google ACK after terminal unknown remains conservatively rejected (cost: actual delivered post may remain unknown; operator checks channel).
5. Existing full-admin market manual retry remains; new UI has no same-day retry. Owner must inspect channel before manually recreating/retrying; no absolute admin resend prohibition claimed.
6. Login and guest inquiry retain separate original quota namespaces; inside each, Bale/SMS share phone/IP budgets (cost: limits are not a single whole-site pooled quota).
7. General direct DB corruption recovery and authenticity of malicious provider payloads are not proven; validated admin API and fail-closed OTP remain the boundary.
8. Existing dev checkouts reused per standing authorization with scoped commits, preserving unrelated frontend HANDOFF.md and PURCHASE_INQUIRY_CURRENT_STATE.fa.md; mixing risk mitigated by explicit paths.
9. Telegram is channel delivery only in this change; phone-to-Telegram login mapping not assumed, matching explicit Bale/SMS answer.

## Release/install
Backend migrations accounts0010 and messaging0016..0019; disabled morning08:00(all7days), both master switches defaultfalse. Existing updater installs tirexa-channel-posts.timer, bounded5 daily runs per tick,30-minute window sameTehran day, no old-day replay. Message rendering supports jalali_date/weekday/site_name only. Current dates at real dispatch, not pre-generated content. Existing market direct/MTProto/Google delivery reused. New platform_errors migration required for destination failures.
Setup learner/Bale.Automation.SETUP.fa.md. PrepareOnly archives are local only; do not confuse with deployment/provider verification. Existing Google morning schedule is independent; avoid enabling duplicate Telegram greeting in both systems.
Sources: https://docs.bale.ai/ and https://docs.bale.ai/safir (official current contract inspected; OTP native object, api-access-key, phone98 and request_id).
