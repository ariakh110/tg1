## 1. Frontend (kavehmetal)
- [x] 1.1 `getGroupGrade(product)` returns the grade label/value (fallback «سایر گریدها»)
- [x] 1.2 `groupProducts` groups by grade and product form instead of factory; section title shows both
- [x] 1.3 Fetch every backend page for the active public-list filters and remove public pagination controls
- [x] 1.4 Calculate row market deltas from positive best prices in the same grade/form group
- [x] 1.5 `npx eslint app/products/page.js`
- [x] 1.6 `npm run build`

## 2. Verification
- [x] 2.1 Production evidence shows separate grade sections (ST52, ST37, CK45…) with factory still visible per row
- [ ] 2.2 After deploy: all CK45 thicknesses appear together without pagination and CK45 row percentages use only the CK45/form group average
