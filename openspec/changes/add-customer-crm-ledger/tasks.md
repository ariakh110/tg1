## 1. Backend (tg1)
- [x] 1.1 Register `customers` in `INSTALLED_APPS`
- [x] 1.2 `Customer` model (phone unique, optional user link, `balance` property) + `CustomerTransaction` ledger model
- [x] 1.3 `makemigrations customers` → `0001_initial`
- [x] 1.4 Serializers: `CustomerSerializer` (with balance + counts), `CustomerDetailSerializer` (with transactions), `CustomerTransactionSerializer` (amount validation per kind)
- [x] 1.5 Admin-only viewsets (`IsAdminOrActiveAdminRole`): `CustomerViewSet` (search/order), `CustomerTransactionViewSet` (filter by customer); `customers/urls.py` router; mount `api/crm/` in `tg1/urls.py`
- [x] 1.6 Django admin: `Customer` (list_display incl. balance) + inline `CustomerTransaction`
- [x] 1.7 `manage.py check` clean

## 2. Frontend (kavehmetal)
- [x] 2.1 `crmApi`: list/create/update customers, list/create transactions
- [x] 2.2 «مشتریان (CRM)» admin tab: customer table with balance, open a customer → transactions + add purchase/payment forms

## 3. Verification
- [x] 3.1 `manage.py check`; `npx eslint` clean on new files
- [x] 3.2 `openspec validate add-customer-crm-ledger --strict`
- [ ] 3.3 After deploy: create a customer, add a خرید and a پرداخت → balance updates correctly; search by phone finds them
