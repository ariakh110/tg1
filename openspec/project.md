# Project Context

## Purpose
Kaveh Metal is a B2B steel marketplace and price-list application. The current product focus is a reliable admin-managed catalog where steel products, prices, origin, availability, taxonomy, and price imports are controlled from the backend and rendered in a Next.js storefront.

The product area must support real steel-market workflows: sheet/coil price lists grouped by factory, rebar by diameter, profile/pipe by dimensions, and admin-controlled options so operators do not type inconsistent category, grade, factory, city, or delivery values.

## Tech Stack
- Backend: Django, Django REST Framework, django-filter, django-mptt, SQLite in development/test, PostgreSQL-compatible architecture.
- Frontend: Next.js App Router, React client components for admin/product interactions, Tailwind CSS, lucide-react icons.
- Docs/specs: OpenSpec change workflow plus the existing steel marketplace documentation pack.
- Data import: CSV/XLSX product price import through backend admin endpoints.

## Project Conventions

### Code Style
- Keep backend domain rules in services/serializers/viewset actions, not ad-hoc frontend-only validation.
- Use explicit serializer fields and queryset filtering.
- Keep frontend state derived from backend APIs where possible; avoid static product taxonomy in UI.
- Use Persian labels in user-facing admin/storefront UI, but keep API values stable ASCII slugs/codes.

### Architecture Patterns
- Product categories are hierarchical with `ProductCategory` and MPTT.
- Product controlled values live in `ProductAttributeOption` with `group`, `product_kind`, optional `category`, optional `parent`, and `is_active`.
- Product specifications use structured fields such as `manufacturing_process`, `surface_finish`, `steel_grade`, `factory`, `cut_type`, dimensions, and diameter.
- Public product lists expose active products only; admin lists include active and inactive products by filter.
- Admin actions must write product audit logs for traceability.

### Testing Strategy
- Backend: run `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`, `python manage.py check`, and `python manage.py test --settings=tg1.settings_test`.
- Frontend: run `npm run lint` and `npm run build`.
- Product taxonomy changes need tests for dependent options, active/inactive visibility, admin list behavior, product validation, and public list filtering.

### Git Workflow
- Preserve dirty unrelated changes.
- Keep migrations committed with their matching model changes.
- Use additive API changes unless a breaking change is explicitly accepted.

## Domain Context
- Sheet (`sheet`) includes sheet and coil manufacturing processes.
- Sheet type/surface includes black, oiled, alloy, galvanized, color, acid-washed, stainless, etc.
- Steel grade depends on sheet type; for example black/acid-washed sheet can use ST37, while alloy sheet can use ST52/CK45/A516/A283.
- Factory depends on sheet/coil process; e.g. sheet can have Mobarakeh, Oxin, Kavian, Khoramabad; coil can have Mobarakeh roll variants.
- Sheet dimensions require thickness and width; sheet needs length and cut type, coil does not need length.
- Origin must be visible as province/city plus delivery place such as warehouse or factory.
- Products without a price must show inquiry/contact behavior; out-of-stock products should lead to order/request flow.

## Important Constraints
- Taxonomy must come from the backend and be searchable/selectable in admin UI.
- Public category/type tabs must be shown only when active products exist.
- Deactivating a product is a soft visibility change and must not remove it from the admin list.
- Product names may be generated automatically from structured specs when the admin leaves the name empty.
- Blog work already moved toward SSR/SEO and should remain independent from product taxonomy changes.

## External Dependencies
- Payment gateway, SMS/email, object storage, Redis/Celery, and maps APIs are planned in the broader marketplace docs.
- The current product price workflow depends mainly on the Django API and local file upload parsing.
