# Change: Restore homepage category families

## Why
The homepage and header replace the six legacy product families with the response from `active-with-products`. When only sheet products are active, every previous category card disappears and the homepage shows a single card.

## What Changes
- Keep the six established product families as the minimum visible set.
- Fetch every page of active product taxonomy instead of only categories that currently have active products.
- Merge taxonomy roots into the established families by stable code and append new roots without duplicates.
- Use the same merged source for homepage cards and header category menus.
- Preserve the established list when the category API is unavailable.

## Impact
- Affected specs: `product-taxonomy`
- Backend schema/API: no change.
- Frontend: public category API helper, family mapping, homepage category cards, and header menus.
