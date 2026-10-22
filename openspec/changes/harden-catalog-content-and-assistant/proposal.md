# Change: Harden catalog assets, editorial HTML and public AI usage

## Why
The 2026-10-22 ECC audit reproduced five security weaknesses. The user authorized necessary improvements and step-by-step implementation updates.

## What Changes
- Enforce catalog asset ownership and immutable parent products.
- Allow only bounded PDF/DWG/DXF documents with matching signatures.
- Sanitize landing HTML on write/read and clean historical records during migration.
- Apply shared-cache atomic burst and daily quotas before public AI calls; fail closed on cache errors.
- Upgrade vulnerable Python dependencies to reviewed fixed versions.

## Impact
- Affected specs: application-security (new).
- Affected code: products, blog, assistant, requirements and deployment documentation.
- Operational impact: Redis must be available for chat; historical active HTML is removed and cannot be restored by reversing the migration. Back up before deployment.
