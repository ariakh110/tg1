# PRD: Product Taxonomy & Price Admin

## Problem / Opportunity

The current product workflow needs a backend-driven taxonomy so admins can publish steel products and update only prices without typing inconsistent values. The storefront must show only categories and sheet types that have active products, while the admin dashboard must keep full visibility over active and inactive products.

The key steel use case is:

`دسته اصلی -> نوع محصول/ورق -> گرید/آلیاژ -> کارخانه -> ابعاد/قطر -> مبدا -> قیمت یا استعلام`

## Implementation Update - 1405/04/22

- The taxonomy category form can create a custom root product kind with a stable technical code such as `angle` or `channel`.
- Saved custom kinds are read from backend category data and become available in controlled-option management without another frontend code change.
- Custom kinds use a generic product form that preserves common dimensions and renders configured controlled options.
- Header, mobile, and homepage category navigation read active categories with products from the backend; built-in families retain their dedicated landing hubs.

For sheets, the admin selects:
- main category: ورق
- manufacturing process: ورق or رول
- sheet type/surface: سیاه، روغنی، آلیاژی، گالوانیزه، رنگی، اسیدشویی، استیل
- grade/alloy filtered by sheet type
- factory filtered by sheet/coil process
- dimensions: thickness and width; length only for sheet
- origin: province, city, delivery place
- price, inquiry, or out-of-stock state

## Users & Use Cases

- Admin/operator: creates product taxonomy, registers products, updates prices by form or Excel, activates/deactivates products, and reviews the whole product inventory.
- Buyer/storefront visitor: chooses a category and sees price lists grouped by factory with readable title, origin, dimensions, price, and inquiry/order actions.
- Future seller/provider: can rely on controlled options for marketplace listings and offers.

## Goals & Success Metrics

- 100% of product form dropdowns are populated from backend APIs.
- No static product taxonomy is required in the frontend.
- Deactivated products disappear from public lists but remain visible in admin lists.
- Sheet grades are filtered by selected sheet type.
- Factories are filtered by selected manufacturing process.
- Admin can download a usable Excel template and import/update rows without changing code.
- All product admin actions are audit logged.

## Functional Requirements

### FR-1 Backend Taxonomy

- `ProductCategory` stores the main visible category tree, including product kind and default/required spec fields.
- A root category may define a new stable custom `product_kind`; child categories inherit their parent's kind.
- `ProductAttributeOption` stores controlled values for manufacturing process, surface finish/type, steel grade, factory, cut type, delivery place, province, and city.
- Option dependencies use `parent`; examples:
  - `steel_grade(ST37)` parent = `surface_finish(black)`
  - `factory(mobarakeh)` parent = `manufacturing_process(sheet)`
  - `city(isfahan)` parent = `province(isfahan)`

### FR-2 Admin Taxonomy UI

- `/admin/dashboard` has a dedicated product taxonomy management surface.
- Admin can create searchable values without typing raw product form values manually.
- Admin can explicitly create a new product kind from the root-category form and then select it for controlled options.
- Admin sees existing values grouped by their purpose and dependency.
- Required dependencies are visible before submit: factory requires sheet/coil parent; sheet grade may require sheet type parent; city requires province parent.

### FR-3 Product Create/Update

- Product form loads category, seller, and option lists from the backend.
- Selecting main category controls visible fields.
- Selecting sheet type controls grade dropdown.
- Selecting sheet/coil controls factory dropdown.
- Sheet requires thickness, width, length, cut type; coil requires thickness and width but not length.
- Price is optional; if missing the storefront shows inquiry/contact behavior.
- Availability controls public CTA: in stock, inquiry, out of stock/register order.

### FR-4 Public Product List

- Category and sheet-type tabs come from active products only.
- Header, mobile, homepage, and category navigation include backend-created root kinds only after they have active products.
- Product rows are grouped by factory for sheet/coil lists.
- Rows show generated title, dimensions, origin as `city - delivery place`, market comparison when available, and price/inquiry/order action.
- Public list hides inactive products.

### FR-5 Admin Product List

- Admin can search/filter all products.
- Admin list can show active, inactive, or all products.
- Deactivate/reactivate is a soft visibility change; it does not delete the product.
- Delete remains a destructive admin action and must be logged.

### FR-6 Import/Export

- Admin can download an Excel template with required headers and sample rows.
- Import can create missing products when requested and update prices for existing product IDs.
- Import reports created, updated, failed rows, and row-level errors.

## Non-functional Requirements

- Product and taxonomy list endpoints must be paginated/filterable.
- Backend validation must reject undefined controlled values.
- Backend validation must reject invalid dependent values.
- UI must remain usable for non-technical operators: searchable dropdowns, Persian labels, clear empty/error states.
- Changes must not break existing public product, order, KYC, or blog APIs.

## Out of Scope

- Real-time automatic market price scraping.
- ERP/WMS inventory synchronization.
- Full payment/escrow implementation.
- Replacing Django admin.

## UX Notes

- Admin dashboard should use a sidebar and separate panels for products, taxonomy, orders, KYC, users, and activity.
- Taxonomy management should be a first-class admin panel, not hidden inside the product creation form.
- Avoid image requirements for products in this workflow.
- Prefer tables/lists and compact management cards over marketing-style layouts.

## Analytics / Tracking

Recommended events/logs:
- `PRODUCT_CREATED`
- `PRODUCT_UPSERTED`
- `PRODUCT_BULK_UPSERTED`
- `PRODUCT_DEACTIVATED`
- `PRODUCT_ACTIVATED`
- `PRODUCT_DELETED`
- `TAXONOMY_OPTION_CREATED`
- `PRODUCT_CATEGORY_CREATED`

## Rollout Plan + Risks

1. Document taxonomy and admin requirements in OpenSpec.
2. Add/adjust backend seed data and validation.
3. Implement taxonomy admin UI and keep product create/import forms wired to it.
4. Run backend and frontend tests/build.
5. Smoke-test `/admin/dashboard`, `/products`, and product detail pages.

Risks:
- Existing records may use older free-text values. Mitigation: accept existing values for display, validate new writes, and provide import cleanup.
- Taxonomy hierarchy can become confusing if categories and options overlap. Mitigation: keep categories for visible catalog grouping, options for controlled spec values.
- Operators can create duplicate values with different spelling. Mitigation: unique `(group, value, parent)` and searchable existing value lists.
