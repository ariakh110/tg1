# Change: Update User Account Workspace

## Why

The user account area currently mixes direct purchases, cart, payments, and marketplace order requests under similar wording. It also renders inside the public site header/footer, so it does not feel like an operational dashboard.

## What Changes

- Rename user-facing navigation so direct Kaveh purchases, cart, settlements, and marketplace load board are clearly separate.
- Convert the authenticated account area into a full-screen workspace with sidebar/topbar similar to the admin dashboard.
- Keep existing routes and APIs stable.
- Improve `/account/dashboard` copy and layout so the next action is clear and user-friendly.

## Impact

- Affected specs: `user-account-workspace`, `direct-sales-dashboard-payments`
- Affected frontend: `AppShell`, `account/layout`, account dashboard, account purchases/payments labels, sidebar naming, marketplace order labels.
- Backend/API: no schema or endpoint changes.

