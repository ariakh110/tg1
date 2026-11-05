# Farda sections seed implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans inline, task by task. Use one independent read-only whole-change reviewer at the end.

**Goal:** Seed the approved 149 angle/channel candidates safely and offline on the next authorized backend update.
**Architecture:** A hash-pinned local data asset feeds one read-only preflight/create-only service and a management command. A durable audit batch makes updates one-shot and retains edits/deletions. A small Bash helper runs preview then explicit apply after migrations.
**Tech Stack:** Existing Django/DRF/MPTT, unittest, Bash; no new dependency or schema.
**Spec:** docs/engineering/bmad-output/specs/spec-angle-channel-catalog-seed/SPEC.md and its two companions; openspec/changes/add-angle-channel-catalog-seed/specs/catalog-seeding/spec.md.

## Global Constraints

- Only the approved 149 products, 8 categories, 18 options; 3 quarantined combinations excluded.
- All new products/categories inactive; products inquiry/noindex; no prices/offers/media or invented facts.
- No overwrite of existing catalog; preserve changed slugs/visibility and deleted records on replay.
- Default command is read-only; explicit apply requires actor label and matching package hash.
- No production invocation, external messages, source scrape, branch merge or push.
- User approved design and local implementation with «بله»; delegated workspace choice. Work in the existing non-main dev-ariakhayer checkout and preserve other changes.

## Review Focus

- Missing/changed package or mismatched release hash must fail before writes (Task 1).
- Same code/name or technical identity resolving ambiguously must abort atomically, never merge by name alone (Task 1).
- Renamed, enriched, deactivated or deleted seeded products must not be resurrected or rewritten (Task 1).
- Failure during specifications/audit must roll back categories, attributes and products together (Task 1).
- Preview failure must prevent release apply, and apply failure must propagate (Task 2).

## Task 1: Pinned atomic seed service and CLI

**Files:** Create products/data/farda_sections_v1.json, products/catalog_seed.py, products/management/commands/seed_farda_sections.py, products/test_catalog_seed.py.
**Consumes:** Approved seed-candidate.json, existing product/taxonomy/spec/dynamic/audit models and content sanitizer.
**Produces:** `load_package(expected_sha256=None) -> (dict, sha256)`; `seed_sections(apply=False, actor='', expected_sha256=None) -> dict`; command `seed_farda_sections [--dry-run | --apply] [--actor LABEL] [--expected-sha256 HASH]`.

- [ ] Write real isolated database tests for no-write preview, 149 inactive imports/65 nominal sizes, no offers, byte-hash failure, actor gate, duplicate technical identity, slug/category/option conflicts, rollback and replay after edits/deletion.
- [ ] Run `manage.py test products.test_catalog_seed --settings=tg1.settings_test --noinput`; expected missing-service RED first.
- [ ] Copy the reviewed asset byte-for-byte. Implement strict pinned loading, read-only preflight, atomic apply and durable ProductAuditLog batch/product identities. Existing matching rows are skipped, conflicting rows fail; no source networking.
- [ ] Add public/admin API and native SEO payload checks in the same database suite; verify public invisibility, stored content and no prices.
- [ ] Run seed + existing matrix/identity suites; expected all green. Commit only named implementation assets/tests and required prepared spec/data.

## Task 2: Offline next-update integration and delivery

**Files:** Create ops/manual_deploy/seed_farda_sections.sh, products/test_catalog_seed_release.py, docs/engineering/reports/farda-seed-implementation.md; modify ops/manual_deploy/update.sh and openspec change tasks; add task-specific handoff.
**Consumes:** Task 1 command and pinned SHA256. Existing updater resolves service Python/DB environment and runs migrations.
**Produces:** Preview followed by apply with explicit release actor; nonzero failure stops the backend update. No remote action is performed during development.

- [ ] Write executable Bash-helper tests with controlled external-Python substitute: preview before apply; failed preview does not apply; failed apply propagates. Expected RED before helper exists.
- [ ] Implement helper and call it immediately after `migrate --noinput`, before unrelated market jobs. Keep schema/matrix behavior unchanged.
- [ ] Run real DB command replay tests; run Bash syntax checks on helper/updater and helper behavior suite. Verify package asset byte hash survives Git archive.
- [ ] Run backend full test suite, Django check/migration consistency, offline source tests and focused native frontend SEO helper checks where feasible. Record baseline failures rather than hiding them.
- [ ] Commit scoped changes, run whole-change read-only independent review and one TDD fix pass for important findings. Record spec/quality reviews, handoff and pending live deployment boundary.

## Plan self-review

CAP-1 data preserved unchanged; CAP-2 taxonomy/spec/dynamic fixtures exercised in Task 1; CAP-3 stored SEO/public invisibility checked in Task 1 with native helper verification in Task 2; CAP-4 preflight/atomicity/replay/release tested across both tasks. Both tasks share the exact CLI/hash contract above; no second implementation coordinator.
