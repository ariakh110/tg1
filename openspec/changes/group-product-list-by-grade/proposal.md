# Change: Group the product price list by steel grade

## Why
The public price list grouped products by factory, producing confusing section titles like «لیست قیمت اکسین» and mixing every grade (ST52, CK45, …) of a factory in one list. Competitors group by grade («قیمت ورق ST52»), which is how buyers actually shop. The store owner asked for grade-separated, grade-titled lists.

## What Changes
- The `/products` listing groups items by steel grade (`steel_grade` / its label) instead of factory. Each grade renders as its own section titled «لیست قیمت <grade>» (e.g., ST52, ST37, CK45); products with no grade fall under «سایر گریدها». The factory remains visible per row (tag + delivery/seller line), so no information is lost.

## Impact
- Affected specs: `product-listing`
- Frontend (kavehmetal): `app/products/page.js` (`getGroupGrade` + `groupProducts`). Frontend-only; no backend or API change.
