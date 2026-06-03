## Context

The direct-sales domain already owns payment, risk, final weight, and loading readiness checks through `StoreOrder`. Driver dispatch should reuse that boundary instead of creating a separate logistics app for the first slice.

## Decisions

- Store logistics models in `sales` because the MVP targets direct `StoreOrder` shipments.
- Use existing `RoleCode.DRIVER` and active `UserRole` records for driver access.
- Compute total shipment weight from final item weight when available, otherwise estimated item weight.
- Use `25_000 kg` as the hard per-assignment planned-weight limit.
- Broadcast offers to selected active drivers, or all active drivers when no explicit list is provided.
- Convert the first accepted offers into assignments until required capacity is filled.
- Keep document files local in the MVP and expose them through serializers; protected streaming can be tightened in a later hardening phase.

## Risks / Trade-Offs

- Without live notifications, drivers must refresh their dashboard.
- Without GPS, assignment status is self-reported.
- Admin must know which drivers to target until driver availability and location are modeled.

## Migration Plan

- Add additive sales logistics tables.
- Existing `driver_name`, `driver_phone`, `vehicle_type`, and `vehicle_plate` fields remain for compatibility.
- No existing order state is changed during migration.
