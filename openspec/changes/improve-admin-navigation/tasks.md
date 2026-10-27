## Design preparation
- [x] Inspect existing destinations, guards and navigation state.
- [x] Capture findability requirements and proposed grouping.
- [x] Prepare architecture/UX drafts and interactive desktop/mobile prototype.
- [x] Check destination coverage and prototype keyboard/mobile behavior.
- [x] Obtain explicit approval of the concrete design (Aria: «اره اوکی هست», 2026-10-27; LangGraph decision recorded).

## Implementation after approval
- [x] Write and self-review the execution plan: frontend `docs/superpowers/plans/2026-10-27-admin-navigation.md`.
- [x] Record explicit implementation authorization (Aria delegated execution without reading; LangGraph decision recorded).
- [x] Add a shared permission-filtered destination registry and search behavior.
- [x] Integrate grouped desktop navigation and mobile drawer without changing business behavior.
- [x] Implement permitted URL state and content navigation continuity.
- [x] Verify role filtering, old labels, browser history, notifications, exact CRM customer shortcut and keyboard behavior (49 Node tests; 15 mocked browser groups on built production UI).
- [x] Complete spec/quality review and handoff; no deployment or real provider send. Frontend reports: `docs/engineering/reports/admin-navigation-{implementation,spec-review,quality-review}.md`.
