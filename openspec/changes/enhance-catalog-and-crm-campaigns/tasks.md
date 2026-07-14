## 1. Specification
- [x] 1.1 Document catalog visuals, ticker/layout behavior, CRM audiences, and provider constraints
- [x] 1.2 Add/update the product PRD and validate the OpenSpec change

## 2. Catalog backend and admin
- [x] 2.1 Add category icon key/image and public-navigation visibility fields with migration
- [x] 2.2 Expose validated icon upload/removal in category APIs
- [x] 2.3 Add curated icon selection and image upload/preview to taxonomy admin
- [x] 2.4 Add backend and frontend tests for category visual metadata

## 3. Storefront presentation
- [x] 3.1 Render uploaded/category-specific icons with a safe fallback
- [x] 3.1a Honor the independent homepage/header/mobile category visibility switch
- [x] 3.2 Balance desktop category columns from the category count
- [x] 3.3 Replace the live-price animation with a continuous right-to-left sequence
- [x] 3.4 Verify desktop/mobile layout and ticker behavior in a browser

## 4. CRM audiences and messaging groups
- [x] 4.1 Add customer product interests and messaging group/member models with migrations
- [x] 4.2 Add customer interest editing and group CRUD/member replacement APIs
- [x] 4.3 Add deduplicated audience preview for customers, groups, product categories, and CRM filters
- [x] 4.4 Extend bulk SMS/Bale delivery with per-recipient logs, daily-cap handling, and Kavenegar batching/tag support
- [x] 4.5 Add backend tests for permissions, preview, deduplication, purchase-derived consumers, groups, SMS, and Bale

## 5. CRM and messaging frontend
- [x] 5.1 Add product-interest controls and single SMS/Bale actions to customer records
- [x] 5.2 Add customer selection, group creation, campaign audience selection, preview, confirmation, and result feedback
- [x] 5.3 Add website/Kavenegar-import group management and member replacement
- [x] 5.4 Add frontend API helpers and lint/build verification

## 6. Delivery
- [x] 6.1 Run Django checks, migration checks, targeted/full tests, frontend lint/build, and strict OpenSpec validation
- [x] 6.2 Commit scoped backend/frontend changes, pull/rebase safely, and push both branches
- [x] 6.3 Rebuild `deploy/backend.tar.gz` and `deploy/frontend.tar.gz` with checksums for manual upload
