# Change: Improve admin navigation findability

## Why

The owner is dissatisfied with the management UI and identified menus and finding sections as the main problem. The current dashboard renders 22 flat panel destinations, a separate content link, duplicate settings access and an unbound header search; mobile uses a long horizontally scrolling row.

## What Changes

- Group existing destinations into five task-oriented groups plus dashboard.
- Add a permission-filtered destination search with old-label aliases and keyboard access.
- Clarify labels, active section and breadcrumb; keep existing IDs and content route.
- Replace the horizontal mobile menu with a searchable drawer.
- Make permitted dashboard selection addressable through URL state.
- Reuse navigation on content management; optionally show three permission-filtered recent destinations.

## Impact

- Affected specs: admin-navigation (new frontend capability specification).
- Affected code: proposed navigation registry/components; AdminDashboardPage and content page integration; existing role helpers remain authoritative.
- No backend API, database, provider-send or financial-rule changes.
- Design draft and prototype: frontend `docs/engineering/bmad-output/planning-artifacts/ux-designs/ux-admin-navigation-20261027/`.
- LangGraph task: `admin-navigation-20261027`. Design approval is pending; this proposal does not authorize product implementation.
