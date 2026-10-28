# Inquiry notifications handoff
Task inquiry-notices-20261028; OpenSpec add-purchase-inquiry-notices.
Implementation complete. See backend docs/engineering/inquiry-notices-verification-20261028.md for actual tests, reviewer fixes and limits; learner/PurchaseInquiry.SETUP.fa.md for activation.
Both packages required. Site notices persist after successful OTP; private Bale delivery requires existing admin bot settings (Bale API, positive private user IDs, enabled toggle). Updater installs independent minute timer. No real sends or deployment performed. Future unknown send recovery must inspect destination before a new attempt.
Preserved unrelated frontend HANDOFF.md and PURCHASE_INQUIRY_CURRENT_STATE.fa.md.
