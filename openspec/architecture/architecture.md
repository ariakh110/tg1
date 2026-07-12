# Architecture

## Goals & Non-goals

Goals:
- Provide a backend-driven steel catalog with admin-controlled taxonomy, prices, availability, origin, and audit logs.
- Keep storefront category/type lists derived from active products, not static UI arrays.
- Support future RFQ/order/escrow workflows documented in `steel-marketplace-docs` without breaking the current product catalog.

Non-goals for the current product-taxonomy work:
- Full ERP/WMS inventory synchronization.
- Real-time price feeds.
- Replacing the existing Django admin; the custom admin dashboard complements it.

## Context & Constraints

The project is currently a Django/DRF backend consumed by a Next.js frontend. Product catalog data is served from `/api/products/`, `/api/categories/`, and `/api/attribute-options/`. Admin product work is done through custom product actions such as `admin-products`, `admin-upsert`, `admin-bulk-upsert`, and `admin-import-template`.

Taxonomy must be stable enough for operators and flexible enough for steel-specific rules:
- `ProductCategory` stores the visible hierarchy and default/required specs.
- `ProductAttributeOption` stores controlled dropdown values and parent dependencies.
- `ProductSpecification` stores the selected structured values on each product.

## High-level Overview (C4: Context/Container)

- Users/admins use the Next.js frontend.
- The frontend calls DRF endpoints through the shared API helper.
- DRF validates category/spec dependencies and persists products, offers, delivery origins, and audit logs.
- The database stores category trees, controlled options, products, specifications, sellers, offers, prices, and delivery locations.

## Key Components

- `products.models.ProductCategory`: hierarchical category tree with code, product kind, spec defaults, required fields, sort order, and active flag.
- `products.models.ProductAttributeOption`: controlled values for manufacturing process, surface finish, grade, factory, cut type, delivery place, province, and city.
- `products.models.ProductSpecification`: structured material data used for filtering, display title generation, and validation.
- `products.views.ProductCategoryViewSet.active_with_products`: exposes only active categories/types that have active products.
- `products.views.ProductViewSet.admin_products`: exposes complete admin product inventory, including inactive products when requested.
- `app/components/admin/AdminDashboardPage.js`: custom admin surface for product creation, price import, taxonomy settings, product list, and audit-facing actions.
- `app/products/page.js`: public product list grouped by backend category/type and comparable steel-grade/product-form groups.
- `app/products/[id]/page.js`: product detail view.

## Data flow / Integrations

1. Admin creates or updates taxonomy values in the dashboard.
2. Admin registers products one-by-one or imports an Excel/CSV file.
3. Backend validates that selected options are defined and, when configured, match their parent option.
4. Public product list fetches active categories and active products.
5. Product list exhausts bounded backend response pages, then groups every matching product by category/type and steel-grade/product-form in one continuous view.
6. Row market deltas compare each positive best price with the arithmetic mean of its displayed grade/form group.
7. Admin activate/deactivate/delete actions write `ProductAuditLog`.

## Quality attributes (performance, security, reliability)

- Product list queries must use `select_related`, `prefetch_related`, bounded backend pagination, and indexed/filterable fields where possible; the storefront retrieves all pages for the active filters before rendering.
- Public endpoints must hide inactive products.
- Admin endpoints must enforce admin permissions and return inactive products only on admin routes.
- Controlled option validation must prevent typo-based inconsistent data.
- Import operations should be row-safe and report partial failures.

## Deployment & Environments

- Local backend runs with `python manage.py runserver`.
- Local frontend runs with `npm run dev`.
- When running frontend builds on Windows, stop any running Next dev process first to avoid `.next/trace` EPERM issues.

## Operational concerns (monitoring, logging)

- Product create/update/import/activate/deactivate/delete actions must write `ProductAuditLog`.
- Order, payment, and KYC audit requirements remain governed by the broader `steel-marketplace-docs` rules.

## Decision log

- See `steel-marketplace-docs/docs/architecture/adr/0001-use-drf.md` for the accepted DRF monolith decision.
- See `changes/add-buy-sell-orders-roles-kyc/` for completed order/role/KYC change documentation.
- Product taxonomy management is tracked by `changes/add-product-taxonomy-admin/`.
