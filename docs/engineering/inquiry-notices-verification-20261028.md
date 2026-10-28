# Purchase inquiry notice verification ? 2026-10-28

OpenSpec: add-purchase-inquiry-notices. LangGraph: inquiry-notices-20261028.

## Implementation/spec review
Successful OTP transaction persists one notice per inquiry (legacy and list); duplicate verification returns original inquiry. No provider call in transaction. Protected assistant-section feed omits private contact; each admin has independent read receipt. A failed notice read still opens the inquiry. Bale settings use existing private admin bot and positive numeric destinations, exact fixed Bale host, independent toggle; no SMS/public market destination. Snapshot recipients, no historical/unconfigured backfill. Text includes reference/contact/count, first five rows and full inquiry link.

Worker claims each target before network. Sent/unknown never automatically retry; stale sending becomes unknown after ten minutes. Recipient IDs normalized before deduplication. Pending capped at30 events/tick. Celery minute schedule and independent systemd minute fallback share DB claims. Updater installs fallback after backend restart. Secure Linux launcher reads backend environment in memory and drops UID/groups for command. No actual environment/secrets read locally. Existing generic inquiry sender is not invoked for purchase intake.

## Real verification
- Backend: manage.py test assistant customers messaging products accounts.test_admin_sections --settings=tg1.settings_test --noinput:269 PASS.
- Django check and makemigrations --check --dry-run: clean.
- Frontend node --test tests/*.test.mjs:66 PASS.
- New JS files/browser test eslint:clean; existing Dashboard5 and AssistantPanel3 baseline errors unchanged, MessagingPanel0.
- npm run build:exit0.
- Production next start on localhost:3000, tests/inquiryNotices.browser.cjs:PASS, readCalls2/feedCalls5/errors[]/unexpected writes[], all APIs mocked.
- Browser checks unread/read/open, new notice toast, stale error retains data, read-failure navigation, focused refresh for newly added inquiry, mobile no overflow, direct link and restricted role zero feed calls.
- Desktop/mobile screenshots inspected; temporary artifacts kavehmetal-inquiry-notices-production.
- Git diff --check clean; Git Bash bash -n update.sh/install_inquiry_timer.sh:PASS.
- RED observed for missing module/model originally; review regressions failed numeric duplicate, missing management command/freshness helper, and browser timed out opening new row82 before fix. All now GREEN.

## Independent quality review and final pass
Fresh read-only reviewer inquiry_notices_review found one Important stale mounted inquiry list, Minor old-unread false toast and equivalent numeric destination duplication. All fixed in single final pass; no open findings. High-water IDs prevent false toast; focusedId refetches list. Browser fixture adds second inquiry only after initial load. Management command tested with dispatcher mocked. No second review requested.

## Operational limits
No live Bale/SMS sent, no deployment. Linux systemd execution not run on Windows; shell syntax only and Django command mocked. Reentrant dispatch test does not prove PostgreSQL multiworker locking. Real delivery requires configured owner bot/private IDs and running backend+timer (or Celery worker/beat). No automatic retries of ambiguous network outcomes; inspect destination first. Site polling30s only while visible; not OS push when browser closed. Throughput/provider latency may exceed a minute.

## Release
Prepare committed backend/frontend archives and canonical updater locally; user installation both required. Migrations assistant0007 and messaging0014. User guide: learner/PurchaseInquiry.SETUP.fa.md. No server publish implied.
