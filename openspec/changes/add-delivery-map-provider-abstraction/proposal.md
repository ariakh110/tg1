# Change: Add delivery map provider abstraction

## Why

Driver dispatch is now geo-aware, but dispatchers and drivers still edit coordinates manually. The workflow should feel closer to ride-hailing systems by showing pickup and driver locations on a map. Neshan is the current preferred provider, but the platform may switch map or routing providers later.

## What Changes

- Add a frontend map-provider abstraction for delivery logistics.
- Use Neshan as the default interactive map provider when the public Neshan map key is configured.
- Keep manual coordinate entry as a fallback when the map provider is unavailable.
- Add interactive map pickers/views to the admin logistics panel, driver operational profile, driver offers/assignments, and buyer order loading context when coordinates exist.

## Impact

- Affected specs: `direct-sales-logistics`
- Affected frontend: map provider helpers/components, admin logistics panel, driver account page, buyer order detail page
- Affected configuration: `NEXT_PUBLIC_NESHAN_MAP_KEY`, optional SDK URL overrides
