# Design

## Provider Boundary

The UI uses a provider-neutral `InteractiveDeliveryMap` component. Screens pass points, a selected coordinate, radius, and callback props. The component delegates rendering to a provider adapter selected by frontend configuration.

Current provider:

- `neshan`
  - Loads the Neshan Mapbox SDK on the client.
  - Requires `NEXT_PUBLIC_NESHAN_MAP_KEY`.
  - Uses latitude/longitude from dispatch data and emits provider-neutral coordinates.

Fallback provider:

- `manual`
  - Renders coordinate controls and point summaries without an external SDK.
  - Used when the provider is not configured or fails to load.

## Configuration

- `NEXT_PUBLIC_MAP_PROVIDER=neshan` by default.
- `NEXT_PUBLIC_NESHAN_MAP_KEY` enables Neshan rendering.
- `NEXT_PUBLIC_NESHAN_SDK_JS_URL` and `NEXT_PUBLIC_NESHAN_SDK_CSS_URL` can override CDN URLs without code changes.

## Routing Future-Proofing

Routing links and route previews should go through the same provider boundary. The first slice focuses on map selection and visual context; route optimization and live navigation remain out of scope.

## Data Boundary

Backend logistics data remains provider-neutral. It stores coordinates, city/province, distance, radius, and offer/assignment status. It does not store Neshan-specific object IDs or map state.
