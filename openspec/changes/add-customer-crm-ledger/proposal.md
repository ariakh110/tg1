# Change: Customer CRM with purchase/payment ledger and balance

## Why
The owner sells steel mostly over the phone and in person — to people who are **not** registered website users. Today there is no place to answer the three questions the owner actually needs at a glance: **who is this customer, what did they buy, and how much do they still owe?** The heavy online machinery (`sales.StoreOrder`, which requires a registered `buyer` user and a full checkout/fulfilment flow) does not fit these offline customers. This change adds a lightweight CRM — the foundation that the later call‑transcription/AI‑analysis phases will attach to (an incoming call number → a `Customer`; an extracted need → an `AssistantInquiry`; a confirmed sale → a ledger `purchase`).

## What Changes
- **Register the existing-but-empty `customers` app** in `INSTALLED_APPS`.
- **New `Customer` model**: name, normalized `phone` (unique key used later to match incoming calls), company, city/province, free note, `extra_phones` (JSON), optional link to a website `user`, `is_active`, timestamps. Exposes a computed `balance` (مانده/بدهی).
- **New `CustomerTransaction` model** — a single accounts‑receivable ledger: `kind` (purchase=خرید / payment=پرداخت / adjustment=تعدیل|مانده اولیه), `amount` (تومان; purchase & payment positive, adjustment may be negative), free‑text `description` (answers «چی خرید» e.g. «۲۰ تن میلگرد ۱۴ ذوب»), `occurred_at`, `created_by`, `created_at`. **balance = Σ(purchase) − Σ(payment) + Σ(adjustment)**; positive = customer owes us.
- **Admin-only CRM API** under `/api/crm/`: `customers` (list/create/retrieve/update/delete, search by name/phone/company, ordered, each row carries `balance`) and `transactions` (filter by customer, create purchase/payment/adjustment). Same permission as the rest of the admin surface (`IsAdminOrActiveAdminRole`).
- **Django admin** registration for both models (inline transactions on the customer page).

Out of scope for this change (later phases): call audio upload, Whisper transcription, AI call analysis, the Flutter app, structured purchase line‑items (phase 1 uses a free‑text purchase description).

## Impact
- Affected specs: `customer-crm` (new capability).
- Backend (tg1): `tg1/settings.py` (`INSTALLED_APPS += customers`), `tg1/urls.py` (`api/crm/`), `customers/models.py`, `customers/admin.py`, `customers/serializers.py` (new), `customers/views.py`, `customers/urls.py` (new), migration `0001_initial`.
- Frontend (kavehmetal): new «مشتریان (CRM)» admin tab (list + balance, open a customer, add purchase/payment) — `app/lib/crmApi.js` (new) + an admin panel component.
- Migration `0001` runs on deploy. No rebuild of existing flows; nothing in `sales`/`orders`/`assistant` changes.
