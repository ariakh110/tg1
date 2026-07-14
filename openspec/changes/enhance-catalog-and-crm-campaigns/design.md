## Context
Product categories are backend-managed and may be created after a frontend release. Messaging already supports Kavenegar SMS and Bale Safir sends with per-recipient logs, but bulk audiences are limited to customer ids or simple CRM filters. Kavenegar's public REST API sends to explicit receptors and supports a `tag`; it does not expose an endpoint that enumerates contact groups stored in the Kavenegar panel.

## Goals / Non-Goals
- Goals: durable category visuals, balanced category layout, a continuous RTL price ticker, reusable CRM groups, SMS/Bale actions inside CRM, and product-consumer campaigns based on site data.
- Non-Goals: synchronizing Kavenegar's private panel address book, replacing the existing providers, adding Celery as a deployment dependency, or inferring product consumption from free-text notes.

## Decisions
- **Category visual fields.** `ProductCategory.icon_key` stores a stable curated key and `icon_image` stores an optional PNG/JPEG/WebP upload. The API exposes both. Uploaded images override curated icons; missing or invalid keys fall back to a domain-aware Lucide icon.
- **Independent public visibility.** `show_in_navigation` controls homepage/header/mobile category visibility without deactivating the taxonomy node or hiding its products and direct URL. This avoids overloading `is_active`, which remains the operational taxonomy state.
- **Safe image upload.** Category images use Django's image validation, a small file-size limit, and raster formats only. SVG is rejected because it can carry executable content when served incorrectly.
- **Balanced desktop grid.** The client computes `rows = ceil(count / 6)` and `columns = ceil(count / rows)`, capped at six. Ten categories therefore render as two rows of five. Existing tablet and mobile breakpoints remain fixed at three and two columns.
- **Continuous ticker.** The ticker renders two identical fixed-width sequences in an LTR animation track while each item remains RTL. Translating exactly one sequence width left makes new prices enter on the right and old prices leave on the left without a visible reset.
- **Product-consumer source.** `Customer.product_interests` is an explicit many-to-many relation to product categories. A product audience is the union of explicit interests and categories from that customer's completed/non-cancelled website order items. Descendants of a selected parent category are included.
- **Reusable groups.** Messaging owns `MessagingContactGroup` and normalized `MessagingContactGroupMember` records. Website groups can be built from CRM customers or pasted numbers. Kavenegar-import groups accept numbers exported from the panel and an optional reporting tag for outbound messages; no fake live-sync capability is presented.
- **Audience resolver.** A single backend resolver accepts customer ids, group ids, product category ids, or CRM stage/source filters, then normalizes and deduplicates recipients. A preview endpoint returns count, sample, invalid count, and source summary before any send.
- **Delivery behavior.** SMS recipients are sent through the existing Kavenegar provider in chunks no larger than 200 receptors per provider call when possible; Bale remains one Safir call per recipient. Existing enable switches, dry-run behavior, daily SMS cap, activity timeline, and per-recipient `OutboundMessage` audit records remain authoritative.
- **Explicit confirmation.** The frontend requires a successful preview and a confirmation action before bulk delivery. Empty audiences and messages are rejected server-side.
- **Permissions.** CRM customer/product-interest endpoints use the `crm` section. Messaging groups, preview, logs, and sends use the existing `messaging` section, already granted to authorized marketers.

## Risks / Trade-offs
- A large Bale campaign remains synchronous because the current deployment does not guarantee a worker process. The UI limits a single campaign and reports partial failures; asynchronous jobs can be added when a managed worker exists.
- Purchase history may not identify every real-world consumer. Explicit product interests let operators correct or enrich the segment without changing historical orders.
- Imported Kavenegar groups can drift from the panel. The UI records the source and last update time and supports replacing the member list.

## Migration Plan
1. Add nullable/defaulted category visual fields, customer interests, and messaging group tables.
2. Deploy backend and run migrations before deploying the frontend.
3. Existing categories, customers, sends, and provider settings continue to work with defaults.
4. Rollback can ignore the additive fields/tables; no existing data is rewritten.

## Open Questions
- Native Kavenegar contact-group synchronization remains unavailable unless Kavenegar publishes a supported group-list API or account-specific integration.

## Verification Record
- Django check and migration drift check passed.
- All 117 tests in `accounts.test_admin_sections`, `messaging`, `customers`, and `products` passed.
- The full 248-test run reached 245 passing tests. Two pre-existing `sales.tests.LoadingVehicleWeighbridgeTests` fixtures still use the removed `unit_price`/`total_price` field names, and one existing CRM follow-up assertion is time-of-day dependent because `timezone.now() + 2h` crosses midnight when the suite runs after 22:00 UTC. None of those failing paths are changed by this feature.
- Targeted ESLint passed and the Next.js production build completed successfully.
- Browser verification rendered ten visible categories as two desktop rows of five and as two mobile columns, with no overlap or horizontal overflow.
- Browser measurement confirmed equal duplicated ticker sequences and a negative horizontal delta, so prices move left while the next sequence enters from the right.
- Admin browser verification covered icon controls, image input, public-visibility PATCH, audience preview, website/Kavenegar-import groups, and desktop overflow.
