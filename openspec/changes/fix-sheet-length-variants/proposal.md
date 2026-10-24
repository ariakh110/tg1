# Change: Preserve sheet length variants
## Why
Admin creation currently overwrites a same-name product regardless of physical length. The user requested separate prices for 6m Kavian sheets and variable sheets longer than 7m, and explicitly confirmed variable lengths.
## What Changes
- Match supplied physical specs for implicit upserts; reject ambiguous name-only matches.
- Add fixed/over length semantics with a positive millimetre threshold; existing rows default to fixed.
- Add admin selection, public labels and prevent interpreting a threshold as exact weight.
## Impact
Products, sales, admin and storefront; additive database migration. Existing overwritten records cannot be recovered automatically. User authorization: bug-fix request and variable-length clarification in this session.
