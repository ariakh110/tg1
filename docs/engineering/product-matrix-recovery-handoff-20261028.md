# Release handoff: matrix correction

Backend implementation commit 9fa85ac; frontend 082fea6, pushed to origin/dev-ariakhayer. 131 backend tests, 60 frontend tests, changed-file lint, production build and mocked production browser passed; see product-matrix-recovery-verification-20261028.md for evidence and independent review fixes.

Local `ops/manual_deploy/deploy.ps1 both -PrepareOnly` succeeded, archives in C:/Users/aria/deploy. PrepareOnly made no server connection. User must install backend.tar.gz and frontend.tar.gz together with update.sh using the existing learner guide KavehMetal.Product-Matrix.fa.md; no new migrations. New backend accepts naming_mode; old backend rejects it, so frontend-only deployment is insufficient.

Actual server incident root cause remains unknown without logs. Verified local fixes address silent malformed responses, explicit no-new results and uncertain-write reconciliation; do not claim live registration success. 34-row test uses ST52 Oxin width2000 at fixed lengths6000/12000. Form preserves values, preview shows existing IDs after possible lost receipt, names may be automatic or per-row manual; existing products remain unchanged.

User clarification requested realistic two fixed lengths; no live data created or provider calls sent. Preserve unrelated frontend docs. Runtime status stored only in canonical backend-local engineering DB. No deferred minor review findings; scoped staging retained non-main checkouts to avoid disturbing unrelated work (cost if wrong: unrelated edits would mix without explicit file staging). Future incident investigation requires actual server/API evidence.
