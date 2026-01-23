
# Steel Marketplace Documentation Pack

This zip contains the following deliverables:

- `docs/architecture/architecture.md` — detailed architecture
- `docs/architecture/adr/*.md` — Architecture Decision Records (ADRs)
- `docs/rules.md` — engineering rules for backend (Django/DRF)
- `docs/design/api-guidelines.md` — REST API guidelines
- `docs/design/ui-guidelines.md` — UI/UX guidelines for Next.js app
- `docs/prd/prd-platform.md` — Product Requirements Document (PRD)
- `openapi/openapi.yaml` — OpenAPI 3.0 spec (YAML)

## Suggested next steps

1. Use `openapi/openapi.yaml` to generate API stubs or a Postman collection.
2. Implement domain models and the state machine described in `architecture.md` and ADRs.
3. Keep `rules.md` enforced via CI (lint, tests, formatting).
