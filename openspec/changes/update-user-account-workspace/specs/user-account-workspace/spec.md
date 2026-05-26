## ADDED Requirements

### Requirement: Account Workspace Shell

The system SHALL render authenticated account pages in a dedicated operational workspace without the public site header and footer.

#### Scenario: User opens account dashboard
- **WHEN** an authenticated user opens `/account/dashboard`
- **THEN** the page renders inside a full-screen workspace shell
- **AND** the public site header and footer are not visible

#### Scenario: User navigates account sections
- **WHEN** the user uses account navigation
- **THEN** the sidebar/topbar remain consistent across account pages
- **AND** navigation labels are visible in Persian

### Requirement: Clear User Domain Naming

The system SHALL use distinct Persian labels for direct purchases, cart checkout, settlements, and marketplace load-board requests.

#### Scenario: User reads account navigation
- **WHEN** the account navigation is displayed
- **THEN** direct purchase history is labeled as `خریدهای من از کاوه`
- **AND** cart is labeled as `سبد خرید مستقیم`
- **AND** pending/payment history is labeled as `تسویه‌ها`
- **AND** marketplace order requests are labeled as `تالار اعلام بار`

#### Scenario: User opens dashboard
- **WHEN** the user opens the dashboard
- **THEN** the dashboard distinguishes direct Kaveh purchases from marketplace load-board requests in the visible copy

### Requirement: User Dashboard Next Actions

The user dashboard SHALL highlight the buyer's most important next action.

#### Scenario: Pending settlement exists
- **WHEN** a user has a pending or overdue settlement
- **THEN** the dashboard highlights the nearest due settlement with amount, deadline, and link to settlements

#### Scenario: Cart has items
- **WHEN** the user has items in the direct cart and no urgent payment action
- **THEN** the dashboard highlights cart completion and links to checkout

#### Scenario: No direct activity exists
- **WHEN** the user has no direct purchases and no cart items
- **THEN** the dashboard offers a clear action to view the price list and start a direct purchase

