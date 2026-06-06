# Design

## Data Model

- `StoreDriverOperationalProfile`
  - One profile per user.
  - Used only for dispatch eligibility and matching.
  - Admin-controlled `is_verified`; driver/admin controlled availability and location fields.
- `StoreDeliveryRequest`
  - Add pickup geo fields, `offer_ttl_minutes`, `auto_reassign_enabled`, `search_radius_km`, and `max_candidate_count`.
- `StoreDeliveryOffer`
  - Add `expires_at`, `notified_at`, `notification_status`, `distance_km`, `match_rank`, and `match_reason`.

## Matching

1. Build candidate drivers from active `DRIVER` role.
2. In auto mode require a verified, available operational profile.
3. Exclude drivers already offered on the request.
4. If request and driver coordinates exist, compute distance via Haversine and keep candidates inside the request or driver radius.
5. If coordinates are unavailable, fall back to exact city/province matching.
6. Sort by distance, then username/id.

Manual selected drivers remain an admin override, but profile metadata is still attached to the offer when available.

## Notifications

The MVP creates internal notification logs through `StoreOrderNotification` with event `DELIVERY_LOAD_OFFERED`. The offer records `notified_at` and `notification_status`. This provides an auditable path for later SMS/push integration without introducing a provider now.

## Expiry/Reassignment

`sales.tasks.expire_delivery_offers` runs every minute. It expires open offers past `expires_at`, logs an event, and calls reassignment for underfilled requests with `auto_reassign_enabled=True`.

Decline also calls reassignment synchronously for faster recovery.

## UI

- Admin logistics panel gets pickup geo fields, driver match preview, TTL/reassignment controls, and driver profile verification.
- Driver page gets an operational profile form and expiry metadata in offers.
