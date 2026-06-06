# PRD: Driver Geo Matching, Offer Expiry, and Reassignment

## Goal

Make direct-order driver dispatch behave closer to a ride-hailing marketplace by finding verified nearby drivers, notifying them, expiring unanswered offers, and reassigning open capacity to the next eligible drivers.

## Scope

- Direct `StoreOrder` delivery requests only.
- Driver eligibility is based on active `DRIVER` role plus an operational driver profile.
- Geo matching uses latitude/longitude when available and falls back to province/city matching.
- Each accepted assignment still follows the hard 25,000 kg capacity rule.

## User Stories

### Admin dispatcher

- As an admin, I can maintain driver logistics profile data: availability, verification, location, vehicle, capacity, and service radius.
- As an admin, I can ask the system to find nearby verified drivers for a loading point.
- As an admin, when I publish a delivery request without manually selecting drivers, the system offers the load to the nearest eligible drivers.
- As an admin, I can manually reassign an underfilled delivery request to selected drivers or ask the system to offer it to the next nearby drivers.

### Driver

- As a driver, I can update my availability, location, vehicle, plate, and service radius.
- As a driver, I receive a time-limited load offer with full shipment details.
- As a driver, I cannot accept an expired offer.

### System

- The system creates an internal notification log for each delivery offer.
- The system expires unanswered offers after the configured TTL.
- The system reassigns expired or declined offers while the delivery request still needs drivers.

## Functional Requirements

1. Driver operational profiles
   - Store one operational profile per user.
   - Profile fields: availability, admin verification, province, city, latitude, longitude, service radius, vehicle type, plate, capacity, and last location timestamp.
   - Only active `DRIVER` users with verified and available profiles are auto-matched.

2. Geo matching
   - If pickup latitude/longitude and driver latitude/longitude exist, calculate approximate distance in kilometers.
   - Match drivers inside either the request search radius or the driver service radius.
   - Sort by distance, then username/user id.
   - If coordinates are missing, match by exact city/province when available.
   - Exclude drivers already offered on the same request.

3. Offer TTL and notifications
   - Delivery offers get `expires_at`, `notified_at`, `notification_status`, `distance_km`, and `match_rank`.
   - Default offer TTL is configurable and defaults to 30 minutes.
   - A `StoreOrderNotification` log is created per offer using event `DELIVERY_LOAD_OFFERED`.

4. Expiry and reassignment
   - A periodic task expires stale `OFFERED` offers.
   - Expired/declined offers trigger reassignment if the request still needs accepted drivers and auto reassignment is enabled.
   - Reassignment never creates duplicate offers for the same driver/request.

5. Admin controls
   - Admin can preview nearby drivers.
   - Admin can publish auto-matched requests.
   - Admin can reassign an existing request manually or automatically.
   - Admin can verify or disable driver operational profiles.

6. Interactive map provider
   - The admin dispatch UI and driver workspace should expose location selection and route context on an interactive map.
   - Neshan is the default map provider for the MVP.
   - The frontend must call maps through a provider abstraction so a later switch to another map or routing provider does not require rewriting dispatch screens.
   - Backend logistics records must remain provider-neutral and store only coordinates, city/province, distance, radius, and route metadata if needed.
   - The UI must continue to work with manual latitude/longitude entry if a map key is missing or the provider script fails to load.

## Non-Goals

- Real push notification provider integration.
- Live GPS tracking while a driver is in transit.
- Route optimization across multiple pickup points.
- Price bidding between drivers.
- Binding backend dispatch logic to a specific map vendor.

## Success Criteria

- A 50-ton order can be auto-offered to the two nearest verified drivers.
- An expired offer cannot be accepted.
- Expired or declined offers are reassigned to the next eligible nearby driver.
- Admin and driver UI expose the new controls without requiring raw API calls.
- Neshan map is used for interactive location selection when `NEXT_PUBLIC_NESHAN_MAP_KEY` is configured.
- Replacing the map provider later is isolated to a map provider adapter instead of admin/driver dispatch screens.
