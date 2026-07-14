# PRD: Homepage Product Category Visibility

## Problem
The public homepage initializes with six product families but replaces them with the `active-with-products` response. Categories without active products disappear, so a catalog state with products only in sheet reduces the entire category section to one card.

## Goal
Keep the established product navigation stable while still reflecting active taxonomy roots created by administrators.

## Requirements
- Sheet, rebar, beam, pipe, profile, and billet remain visible as the baseline public families.
- All pages of active categories are loaded from the backend.
- Same-host pagination links cannot downgrade an HTTPS API request to HTTP.
- Active root categories are merged by code; existing codes update labels and children while retaining their established visual treatment.
- New active roots are appended once and link to their dynamic family hub.
- Child categories are used for subtitles but are not rendered as separate family cards.
- API failure leaves the baseline list untouched.
- Homepage desktop/mobile grids and header desktop/mobile menus use the same merged list.

## Acceptance Criteria
- Production taxonomy returns more than one page and every active coded root is represented.
- The previous six cards are visible even when only one has active products.
- No duplicate family code is rendered.
- Layout remains responsive with the expanded number of cards.
- Frontend lint/build and strict OpenSpec validation pass.

## Out of Scope
- Hiding a baseline family based on inventory.
- Reordering families from the homepage UI.
- Adding new icon assets for every custom category.
