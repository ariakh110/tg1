# Copilot Instructions for AI Agents

## Project Overview
This repository contains a Django REST API backend (`tg1/`) and a Next.js frontend (`kavehmetal/`).

### Backend (`tg1/`)
- **Framework:** Django + Django REST Framework
- **Key Apps:**
  - `products/`: Product catalog, filtering, offers, specifications, images, documents
  - `carts/`, `orders/`, `customers/`: E-commerce flows
  - `core/`: Shared models, serializers, utilities
  - `utils/`: Abstract models and helpers
- **API Patterns:**
  - Uses `ModelViewSet` for CRUD endpoints
  - Filtering: `django-filter` with custom filters (e.g., `ProductFilter`, `OfferFilter` in `products/filters.py`)
  - Pagination: `StandardResultsSetPagination` (12 items/page default)
  - Permissions: `IsAuthenticatedOrReadOnly` by default
  - Related data: Uses `select_related`/`prefetch_related` for query optimization
- **Testing:**
  - Tests are in each app's `tests.py`
- **Build/Run:**
  - Local: `python manage.py runserver`
  - Docker: See `docker-compose.yml`

### Frontend (`kavehmetal/`)
- **Framework:** Next.js (see `README.md` for dev commands)
- **Entry:** `app/page.js`
- **Start:** `npm run dev` (or `yarn dev`, etc.)

## Conventions & Patterns
- **Serializers:** Read and write serializers are separated for complex models (e.g., `ProductListSerializer`, `ProductWriteSerializer`)
- **Filtering:** Use `filterset_class` for complex filters, `filterset_fields` for simple ones
- **Custom Endpoints:** Use `@action` in ViewSets for nested or non-CRUD endpoints (e.g., `/products/{pk}/offers/`)
- **Model Relationships:** Prefer explicit foreign keys and related names
- **API Versioning:** Not currently implemented

## Integration Points
- **DjangoFilterBackend**: Used for filtering in most ViewSets
- **REST Framework Pagination**: Standardized via `StandardResultsSetPagination`
- **Docker**: Use `docker-compose.yml` for multi-service orchestration

## Examples
- To add a new filter: create a filter class in `products/filters.py` and set `filterset_class` in the ViewSet
- To add a new API endpoint: add a method with `@action` in the relevant ViewSet

## References
- Key files: `products/views.py`, `products/filters.py`, `core/models.py`, `docker-compose.yml`, `kavehmetal/README.md`

---
If you are unsure about a workflow or convention, check the relevant app's `views.py` or `filters.py` for examples.
