## 1. Preparation
- [x] 1.1 Inspect existing models, import/matrix behavior and SEO consumers.
- [x] 1.2 Collect only factual angle/channel tables and their subgroups, excluding tees and all other families.
- [x] 1.3 Normalize/deduplicate with provenance, quarantine source errors and produce review JSON/CSV and original Persian content.
- [x] 1.4 Validate the data offline and compare field names/types/limits against current models.
- [ ] 1.5 Obtain explicit approval of this design, angle-unit mapping and unpublished defaults.

## 2. Application implementation after approval
- [ ] 2.1 Write isolated DB tests for preview, apply, replay, conflicts, rollback and edited/deleted records.
- [ ] 2.2 Implement offline atomic create-only seed command with audit and review gating.
- [ ] 2.3 Verify taxonomy/spec/dynamic-size/API/SSR behavior without fake offers and without changing sheet matrices.
- [ ] 2.4 Add and test an explicit one-shot release entrypoint using the reviewed package hash.
- [ ] 2.5 Complete spec/security reviews and handoff; deployment remains separately authorized.
