# Change: Configurable per-product roll weight

## Why
In roll (coil) sales the weight of each roll was a hardcoded rule — 22.5 ton for thickness ≥ 3mm, else 20 ton — with no way to set the real weight of a specific roll. The store needs to enter the actual fixed roll weight per product so pricing (price × weight) and the estimated invoice match reality.

## What Changes
- **Roll weight resolution honors the product's «وزن واحد» (`weight_kg_per_unit`).** `default_coil_weight_ton` (and the frontend `defaultCoilWeightTon`) now return `weight_kg_per_unit / 1000` when that field is set (> 0), and fall back to the existing 20 / 22.5-ton thickness default otherwise. The order selection records `roll_weight_rule = "configured"` when the per-product weight is used.
- **Admin product form exposes the field.** When a sheet product's process is رول (coil), the admin product form shows a «وزن هر رول (kg)» input (optional; empty = the 20/22.5 default). It is saved to the spec via the existing admin upsert.
- No data migration; `weight_kg_per_unit` already exists on `ProductSpecification`.

## Impact
- Affected specs: `product-pricing`
- Backend (tg1): `sales/services.py` (`default_coil_weight_ton` + `roll_weight_rule`), `sales/tests.py` (new test).
- Frontend (kavehmetal): `app/lib/storeSalesApi.js` (`defaultCoilWeightTon`), `app/components/admin/AdminDashboardPage.js` (roll-weight input + form wiring).
