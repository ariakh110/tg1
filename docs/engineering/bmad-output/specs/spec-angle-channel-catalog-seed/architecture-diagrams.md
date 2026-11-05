# جریان داده

CURRENT: مدل‌ها و renderer موجودند؛ collector و بستهٔ بررسی این مرحله آماده شده‌اند.
PROPOSED: قسمت apply/import و اتصال به به‌روزرسانی پس از تأیید، هنوز ساخته نشده است.

```mermaid
flowchart LR
  Public[Public angle/channel tables] --> Snapshot[Versioned factual snapshot]
  Snapshot --> Review[Normalized review candidate + CSV]
  Review --> Approval{Owner design approval}
  Review --> Quarantine[Invalid source rows]
  Approval -->|PROPOSED| Preview[Offline seed dry-run]
  Preview -->|PROPOSED explicit apply| Atomic[Atomic create-only transaction]
  Atomic --> Taxonomy[ProductCategory + ProductAttributeOption]
  Atomic --> Product[Product + ProductSpecification + dynamic specs]
  Atomic --> Audit[ProductAuditLog]
```

```mermaid
erDiagram
  ProductCategory ||--o{ Product : category
  Product ||--|| ProductSpecification : specifications
  Product ||--o{ SpecificationValue : dynamic_specs
  SpecificationAttribute ||--o{ SpecificationValue : attribute
  ProductCategory ||--o{ ProductAttributeOption : optional_scope
  Product ||--o{ ProductAuditLog : audit_logs
```

ERD یک زیرمجموعهٔ تأییدشده از مدل‌های فعلی است؛ seed رابطهٔ جدیدی اضافه نمی‌کند.
