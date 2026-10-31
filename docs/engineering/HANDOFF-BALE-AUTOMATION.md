# Bale daily posts and verification delivery handoff
Completed locally2026-10-31. User request daily channel text/morning; choice Bale/SMS OTP. OpenSpec add-bale-channel-automation; LangGraph bale-automation-20261031. Backend design and verification docs dated20261031; frontend plan docs/superpowers/plans/2026-10-31-bale-automation.md.

New channel-posts admin API with preview/history, unique daily snapshot and independent platform outcomes. Existing Bale Bot API / Telegram transports inclGoogle reused. Native Safir OTP available for login/binding/guest inquiry, no silentSMSfallback, shared per-flow cooldown/budgets retained. Already-signed-in inquiry remains noOTP. New UI messagingtab «انتشار روزانه کانال», flags and customer methods. Morning seed08:00disabled, all7days. accounts0010/messaging0016..0019 and bothpackages required. updater installs tirexa-channel-posts.timer.

329backend,72node,fourmockedbrowser suites, build/lint/checks pass. One fresh final review;3Important+1regradedImportant fixed viaRED→GREEN. No re-review. Exact findings/evidence/boundaries in backend bale-automation-verification-20261031.md. Guide learner/Bale.Automation.SETUP.fa.md. No live send/provider config/deploy. Owner enables Safir+OTP and mobileauth, channel config/global/row switches. Queued/reserved sends not recalled; no same-day retry UI. Old Google greeting independent, avoid doubleTelegrammorning.

Preserve unrelated frontend HANDOFF.md and PURCHASE_INQUIRY_CURRENT_STATE.fa.md. Scoped feature handoff supplements them. Prepared archives are not a production deployment.
