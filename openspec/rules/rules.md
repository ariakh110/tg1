# Engineering Rules

## Code style (formatting, naming)

- Backend code follows Django/DRF conventions with explicit serializer fields and clear viewset actions.
- Frontend components should use the existing Tailwind/lucide style and Persian UI labels.
- Do not hard-code product taxonomy in the frontend. Categories, types, grades, factories, cities, and delivery places must be fetched from the backend.
- Keep API codes/values stable and ASCII where possible; display labels can be Persian.

## Testing policy (unit/integration/e2e)

Required backend checks for product/taxonomy changes:
- `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`
- `python manage.py check`
- `python manage.py test --settings=tg1.settings_test`

Required frontend checks:
- `npm run lint`
- `npm run build`

Product taxonomy tests must cover:
- only active products in public product lists,
- inactive products visible in admin lists by filter,
- dependent dropdown values for sheet type -> grade and sheet/coil -> factory,
- product validation rejects undefined or invalid dependent options,
- product audit log creation for admin actions.

## Error handling & logging

- Backend validation errors should be explicit and safe for display.
- Bulk imports should return row-level errors instead of failing silently.
- Admin product actions must create `ProductAuditLog` entries.

## Security basics (secrets, input validation)

- Admin-only product/taxonomy endpoints must enforce admin permissions.
- Public endpoints must not expose inactive products.
- Do not rely on frontend validation for controlled taxonomy correctness.
- Never commit secrets or local credentials.

## Code review checklist

- Does the change introduce static taxonomy in the frontend? If yes, reject it.
- Are active/inactive visibility rules correct for public and admin contexts?
- Are option dependencies validated server-side?
- Are imports backward-compatible with the existing Excel/CSV template?
- Are migrations included when models/seed data changed?
- Are related docs/OpenSpec/OpenAPI updated if the contract changed?

## Branching / commit message conventions

- Keep changes scoped to the requested feature.
- Preserve unrelated dirty files.
- Prefer additive API changes.

## Definition of Done

- Docs/specs updated when behavior changes.
- Backend and frontend checks pass.
- Admin workflow can create taxonomy, create/update products, import prices, deactivate/reactivate products, and still view inactive items in the admin list.
