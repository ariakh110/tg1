# معماری: وضعیت موجود و مقصد

```mermaid
flowchart LR
  PublicAPI[CURRENT Product list API] --> Model[PROPOSED family-specific display model]
  Model --> Board[Factory / form / grade tables and mobile rows]
  Admin[Admin exact pricing rows] --> List[PROPOSED admin-price-rows GET]
  Admin --> Update[admin-bulk-prices POST]
  Update --> Validate[Admin permission / existing tier / expected price / positive value]
  Validate --> Atomic[Atomic locked update of unit_price + verified_at]
  Atomic --> Audit[Existing audit / price snapshot]
  Generic[CURRENT generic CSV product importer] -. separate .-> Product[Product / Specification / Offer]
```

```mermaid
erDiagram
  Product ||--o{ Offer : existing
  Offer ||--o{ PricingTier : existing
  Seller ||--o{ Offer : existing
  Product ||--o| ProductSpecification : unchanged
  Product ||--o{ SpecificationValue : unchanged
  Product ||--o{ ProductAuditLog : audit
```

قفل tierها به ترتیب id؛ اعتبارسنجی مجدد expected_price داخل transaction. هیچ
Product/Offer/Spec/Delivery save یا create/delete در service فقط قیمت مجاز نیست.
اگر خطا باشد batch کامل rollback می‌شود؛ history/audit جزو همان transaction است.
GET قیمت‌ها admin-only و paginated؛ دادهٔ عمومی یا قیمت حداقل، شناسهٔ نوشتن نیست.
