# Change: Enhance catalog presentation and CRM campaigns

## Why
The storefront category cards do not give new taxonomy roots a meaningful visual identity, the live-price strip visibly resets, and a fixed six-column grid produces unbalanced rows. The existing SMS and Bale providers also are not connected to practical CRM campaign audiences such as saved groups and consumers of a specific product family.

## What Changes
- Add a curated icon key, an optional uploaded raster image, and an independent storefront-navigation visibility switch to product categories; an uploaded image takes precedence over the icon key.
- Render homepage categories in balanced responsive rows and make the live-price ticker move continuously from right to left without a reset jump.
- Add explicit product-interest categories to CRM customers while retaining purchase history as an additional source of product-consumer membership.
- Add reusable messaging groups with website and Kavenegar-import sources, normalized and deduplicated phone members, and an optional Kavenegar tag.
- Add audience preview and bulk campaign delivery over SMS or Bale for selected customers, saved groups, and product-consumer segments.
- Add CRM controls for single-customer messaging, customer selection, product-interest editing, group creation, campaign preview, and send confirmation.
- Keep every outbound attempt in the existing per-recipient audit log and apply the existing channel switches and SMS daily cap.

## Impact
- Affected specs: `product-taxonomy`, `storefront-navigation`, `customer-crm`, `messaging`
- Backend: `products`, `customers`, and `messaging` models, serializers, services, views, migrations, and tests
- Frontend: homepage/header catalog presentation, taxonomy admin, CRM workspace, messaging settings/group management, API clients, and styles
- Deployment: additive database migrations and refreshed frontend/backend deployment archives
