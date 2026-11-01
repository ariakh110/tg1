# Industrial exchange usability
## Why
Owner reports unreadable map, table too low, unclear filters and missing sponge iron/industrial groups. Live public API2026-11-01 confirms60 sponge-related historical rows grouped under ore chain; importer explicitly retains steel chain only.
## What Changes
Table-first compact page, clear date/group/producer/trade-state filters and reset, explicit empty-date recovery, optional high-contrast map with accessible text controls. Industrial ingestion/classification, independent sponge category and migration of old sponge rows, normalized Persian search, all-stored-day selection and cross-day group availability metadata.
## Impact
products ingestion/publicAPI/data migration; commodity-exchange frontend only. Existing units/raw/source/history retained; no provider/credentials/Safir changes. Bale templates approval recorded but IDs not supplied; no inferred template integration.
