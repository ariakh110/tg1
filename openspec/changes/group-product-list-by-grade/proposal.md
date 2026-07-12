# Change: Show complete product groups with comparable market averages

## Why
The public price list originally grouped products by factory, producing confusing section titles like «لیست قیمت اکسین» and mixing every grade (ST52, CK45, …) of a factory in one list. The later grade grouping still split one product group across 12-item UI pages, so CK45 thicknesses such as 8–30 mm could not be reviewed together. Row market percentages also used the average of the entire selected sheet category, which made CK45 prices look artificially high when compared with unrelated ST37 products.

## What Changes
- The `/products` listing groups items by steel grade and product form (factory sheet, cut sheet, or coil). Each comparable group renders as its own section; products with no grade fall under «سایر گریدها». Factory and delivery/seller information remain visible per row.
- The storefront exhausts the backend's paginated product response and renders every active product matching the selected category, type, search, and ordering in one continuous view without public pagination controls.
- Each row's «بالاتر/پایین‌تر از بازار» percentage uses the arithmetic mean of positive best prices inside that same displayed grade/form group. Products without a price are excluded from the mean.

## Impact
- Affected specs: `product-listing`
- Frontend (kavehmetal): `app/products/page.js` (complete-page fetching, grouping, and market comparison).
- Documentation: product-listing PRD and architecture are aligned with the continuous list and group-local comparison.
- Backend/API: no contract change; DRF pagination remains an internal transport boundary.
