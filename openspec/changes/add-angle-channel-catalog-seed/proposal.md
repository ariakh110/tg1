# Change: Prepare and safely seed angles and channels

## Why

The owner wants only FardaFoolad angle/channel catalog facts prepared for the next
site update, with native taxonomy, technical details and SEO. The current product
matrix is deliberately sheet/coil-only, and the existing seed_products command is
sample data, not a safe production catalog importer.

## What Changes

- Completed preparation: versioned factual snapshots, provenance, deduplicated
  review JSON/CSV, original Persian content and offline validation. No live DB writes.
- Proposed after design approval: offline create-only seed command, transactional
  apply, dry-run, conflict/audit handling and explicit next-release invocation.
- Proposed categories: angle (construction/ST52/5SP), channel
  (construction/Europe group/European-equivalent); reuse current models.
- Inactive/noindex/inquiry defaults, no source offers/prices/images/stock, no
  invented dimensions/grade/weight/standard and no source scrape during deploy.

## Impact

- Affected specs: catalog-seeding (new delta).
- Prepared artifacts: docs/engineering/research/farda-angle-channel/.
- BMAD contract: docs/engineering/bmad-output/specs/spec-angle-channel-catalog-seed/.
- Future application changes: a focused products seed service/management command,
  its isolated database tests and a reviewed release entrypoint. Not implemented yet.
- No schema/API/frontend product-matrix change is proposed in this slice.

## Authorization and status

The owner subsequently approved the concrete integration with «بله» and delegated
workspace choice. Local implementation now exists (service/CLI/tests and offline
next-update helper). The earlier preparation wording above is historical; see
docs/engineering/reports/farda-seed-implementation.md for current verified status.
No live import, push, merge or deployment was performed or authorized by this work.
