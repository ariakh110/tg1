# مستندات پروژه «بازارگاه آهن‌آلات و خدمات صنعتی»

این پوشه شامل مستندات فنی و محصول برای یک پلتفرم بازارگاهی (Marketplace) در حوزه خرید/فروش آهن‌آلات و خدمات صنعتی (برشکاری، حمل‌ونقل، کنترل کیفیت و ... ) است.

- Backend: **Python / Django / Django REST Framework**
- Frontend: **Next.js**
- مدل کسب‌وکار: **B2B Marketplace** با جریان‌های RFQ (BUY)، اعلام فروش/بار (SELL) و همچنین «خدمات» مشابه مدل اوبر.

## ساختار پوشه‌ها

```
steel-marketplace-docs-fa/
├── docs/
│   ├── architecture/
│   │   ├── architecture.md
│   │   └── adr/
│   │       ├── 0001-use-drf.md
│   │       ├── 0002-order-decomposition.md
│   │       ├── 0003-escrow-payment.md
│   │       └── 0004-order-state-machine.md
│   ├── rules.md
│   ├── design/
│   │   ├── api-guidelines.md
│   │   └── ui-guidelines.md
│   └── prd/
│       └── prd-platform.md
└── openapi/
    └── openapi.yaml
```

## نحوه استفاده

1. از **PRD** شروع کنید تا نیازمندی‌های محصول و MVP مشخص شود:
   - `docs/prd/prd-platform.md`
2. سپس معماری کلان و تصمیم‌ها را ببینید:
   - `docs/architecture/architecture.md`
   - `docs/architecture/adr/*`
3. برای استانداردهای توسعه و کدنویسی:
   - `docs/rules.md`
4. برای استانداردهای API و UI:
   - `docs/design/api-guidelines.md`
   - `docs/design/ui-guidelines.md`
5. برای قرارداد API و هماهنگی تیم‌ها:
   - `openapi/openapi.yaml`

> پیشنهاد: این مخزن/پوشه را کنار کد پروژه نگه دارید و از طریق Pull Request برای تغییرات مستندات نیز بازبینی انجام دهید.
