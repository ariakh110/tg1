# Current engineering handoff: catalog board and amount-only editing

2026-11-06: owner approved «بله، همین طرح را اجرا کن». Workflow task
`catalog-board-price-only`; implementation on existing dev-ariakhayer branches.
Backend48fa9ea/594902c/1ee3b9e/35fa37a; frontendbaff473/15b2225/e74ca20. Factory/family responsive
board plus exact existing-tier amount-only editor implemented; no schema change.
511 isolated Django tests,93 Node tests, touched ESLint and native Next build pass
after one independent review and one six-finding TDD fix pass.14 local browser
scenarios passed before final fixes; final browser/device smoke remains a release
check because additional preview execution was blocked by host policy, not bypassed.
No unresolved Important/Critical from review; two declared Minor notes remain.
Query workflow status and final reports before continuing with integration.
Task handoff: HANDOFF-CATALOG-BOARD.md. Reports: reports/catalog-board-*.md.
Do not upload verification `.next` (built with loopback fixture URLs); build from
source with real server environment only after separately authorized release.
No live writes/deploy/provider sends/merge/push. Frontend unrelated HANDOFF.md and
PURCHASE_INQUIRY_CURRENT_STATE.fa.md edits remain preserved and uncommitted.

## Previous completed task: angle/channel seed implementation

2026-11-05: user approved the offered design/implementation with «بله» and delegated
workspace choice. Current dev-ariakhayer checkout retained. Implementation and 501
backend tests pass locally. Command defaults to read-only; release helper previews
then applies the pinned inactive/noindex/inquiry package once after migrations.
149 products (84 angles/65 channels), 8 categories, 18 scoped options; no prices,
offers or invented weights. No schema/matrix change. Public inactive detail,
summary, specifications and dynamic values are hidden from non-admin, retaining
admin preview. Scope/case option identity and numeric nominal matching are fixed.

Current report: docs/engineering/reports/farda-seed-implementation.md.
Plan: docs/superpowers/plans/2026-11-05-farda-sections-seed.md.
Workflow task: angle-channel-catalog-seed; query tools/engineering.ps1 status before
continuing. One independent review and one TDD fix pass completed:3 Important
fixed;1 Minor (two extra rollback injection locations) deferred. Final full suite
501/501 (36.177s);53 focused pass. Runtime commits f5eee1f/e68c255/a10fc4e.
Task-specific final handoff: docs/engineering/HANDOFF-FARDA-SEED.md.
No live DB import, deployment, provider sends, branch switch/merge or push.
Preserve audit receipts: replay must not resurrect deleted or edited rows.
No frontend files changed; its unrelated handoff modifications were preserved.

## Historical preparation handoff (superseded by status above)

# Angle/channel catalog preparation

Date: 2026-11-05. Task: angle-channel-catalog-seed.
OpenSpec: openspec/changes/add-angle-channel-catalog-seed/.
BMAD: docs/engineering/bmad-output/specs/spec-angle-channel-catalog-seed/.

## Objective and actual status

The owner requests only FardaFoolad angles/channels as seed data for a later update,
with native categories, technical facts and SEO. Data/design preparation is complete;
application importer, matrix extension, release hook and live import are NOT complete.
The workflow is to stop at design_approval, without fabricated approval.

## Prepared evidence

docs/engineering/research/farda-angle-channel/ contains source-catalog.json,
seed-candidate.json, products-review.csv, quarantine-review.csv, Persian README,
read-only collector, offline compiler, tests and model-field validator.
467 source observations -> 149 unique candidates (84 angles, 65 channels) plus
3 quarantined combinations. 8 proposed categories, 16 factories and 2 explicit
grades. 42 candidates have no manufacturer identified in the source brand column.
Unverified fields remain unset; source stock, offers, prices, images and marketing
were not imported. Products/categories are proposed inactive; products inquiry/noindex.

## Actual checks

8 offline unittest checks passed; a collector regression first failed on tables
with a grade column instead of brand, then passed with ST52/5SP included. Candidate
matches its offline compiler exactly. Model names/types/choices/limits validated
for 149 candidates, 8 categories, 18 controlled options; Django check passed.
OpenSpec 1.14.3 strict validation passed. VALIDATION.json records commands/results.
No SQL-backed seed test, frontend build, provider send, release or production check.
Research/data review is by the same coordinator, not an independent reviewer.

## Decisions and next action

The current product matrix explicitly remains sheet-only. Do not bypass its guard
or run the sample seed_products command to import this candidate. The JSON is NOT
a Django fixture. No fixed database IDs are included.
Ask for design confirmation: independent angle/channel families, angle-unit mapping
to mm and initial unpublished defaults. After approval follow the checkpoint/plan,
implement an offline atomic create-only command with dry-run/conflict/audit/replay
tests, then review the actual release entrypoint before wiring a one-shot hook.
Future apply must preserve administrator-edited/deleted/deactivated records.

## Preserved earlier handoff

# Engineering handoff: toolchain installation

## Objective/status
Install a shared Claude Code / Codex engineering workflow. Completed locally on 2026-10-25.

## Accepted decisions
User requested execution for both tools. Existing backend OpenSpec retained. BMAD 6.12.4 stable; Superpowers 7.0.1 pinned; official frontend-design pinned. Project-local skills, no plugin hooks. One implementation coordinator per item.

## Files
See toolchain-lock.json, AGENTS.md, CLAUDE.md, WORKFLOW.md, PROJECT_CONTEXT.md, START.fa.md. Both discovery directories contain 46 skills and 300 identical files. Personal BMAD configuration/rendered caches remain ignored.

## Verification
verify_toolchain.py --runtime passed in both repositories. uv 0.13.5 installed from official GitHub release and archive SHA256 verified. BMAD build workflow rendering succeeded for the Codex backend and Claude frontend paths. This validates files/config/runtime, not a live Claude session: Claude executable is not on the current PATH.

## Next action
Start a fresh Codex/Claude Code session at an application repository root, invoke kaveh-engineering, then select the feature to analyze. The learner workspace also has a launcher to locate both repositories. Restart the terminal if uv is not discovered on its old PATH.

## Product/deployment
No product behavior, runtime dependency, database schema or server deployment changed. No real provider messages sent. Existing release bundles were not rebuilt for development-only tooling.
