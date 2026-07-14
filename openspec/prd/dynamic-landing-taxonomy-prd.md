# PRD: Dynamic Landing Families from Product Taxonomy

## Problem
The product taxonomy can be extended from the admin dashboard, but the landing editor and public family routes still use a compiled list of six family codes. New top-level categories are therefore absent from the editor and their landing routes can return 404.

## Goal
Make product taxonomy the operational source of truth for cluster landing families so an admin can create a new active root category and immediately author SEO landings for it.

## Functional Requirements
- The landing family selector lists every active root product category with a non-empty code.
- The category request follows pagination and does not stop at the first API page.
- Child categories are not family options because they belong under a root family.
- Existing landing family values remain visible during edit even when the category has been deactivated or renamed.
- Public `/category/<family>` pages accept active taxonomy root codes.
- Public `/category/<family>/<slug>` pages do not reject valid active landings because their family is absent from a static frontend list.
- Sitemap generation includes dynamic family hubs and active landing URLs.

## Acceptance Criteria
- Creating an active root category in the taxonomy panel makes it appear in the landing form after refresh.
- Creating a landing for that family produces a working public URL without rebuilding a family allowlist.
- Inactive roots, children, and code-less categories are excluded from new landing selection.
- Existing six legacy families continue to work.
- Frontend lint/build and strict OpenSpec validation pass.

## Out of Scope
- Automatic landing generation from taxonomy records.
- Changing the landing database relation from a string family code to a foreign key.
- Treating every taxonomy child as a separate family URL.

