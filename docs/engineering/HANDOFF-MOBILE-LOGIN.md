# Mobile SMS login handoff
Feature optional mobile login/signup and authenticated verified phone binding. User requested SMS login and settings enable/disable; implementation authorized, no live sends/deploy.
OpenSpec add-mobile-sms-login; LangGraph mobile-sms-login-20261028; design backend docs/engineering/mobile-login-design-20261028.md, frontend plan docs/superpowers/plans/2026-10-28-mobile-sms-login.md; actual checks backend mobile-login-verification-20261028.md.
Activation guide learner/MobileLogin.SETUP.fa.md. Both packages and accounts0009/core0010/messaging0015 migrations required. SiteSettings flag defaultoff; admin Settings enables. Messaging login_otp_template separate; valid configured Kavenegar required. Existing users must bind own phone after password/Google authentication, not implicit unverified profile matching. No auto transfer of existing bound number.
Preserve frontend unrelated HANDOFF.md and PURCHASE_INQUIRY_CURRENT_STATE.fa.md. No new app runtime dependency.
