## 1. Backend (tg1)
- [x] 1.1 `default_coil_weight_ton`: use `weight_kg_per_unit / 1000` when set, else 20/22.5 default
- [x] 1.2 `normalize_order_item_selection`: `roll_weight_rule = "configured"` when per-product weight used
- [x] 1.3 Test: coil order uses configured `weight_kg_per_unit`
- [x] 1.4 `manage.py check` + targeted coil tests pass

## 2. Frontend (kavehmetal)
- [x] 2.1 `defaultCoilWeightTon`: honor `weight_kg_per_unit` (kg→ton) with default fallback
- [x] 2.2 Admin product form: «وزن هر رول (kg)» input shown for رول (coil) + wired into state/payload/edit-load

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-configurable-roll-weight --strict`
- [ ] 3.3 After deploy: set «وزن هر رول» on a coil product → buy page shows that weight; order estimate uses it; empty field keeps 20/22.5 default
