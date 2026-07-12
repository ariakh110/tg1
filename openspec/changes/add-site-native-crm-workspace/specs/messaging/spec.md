## ADDED Requirements

### Requirement: Bale Operator Identity and Authorization
Internal Bale CRM operations SHALL require a verified binding between a Bale user id and an active website user. Authorization SHALL use the website user's current roles and admin-section permissions for every command and callback. A configured group id or text allowlist alone MUST NOT grant CRM write access.

#### Scenario: Bound marketer uses CRM command
- **WHEN** a Bale user is bound to an active website user with CRM section access
- **THEN** the user can run CRM commands allowed by that role

#### Scenario: Removed role takes effect immediately
- **WHEN** CRM access is revoked from the bound website user
- **THEN** the next Bale command is denied without changing CRM data

### Requirement: Stateful and Idempotent Bale CRM Wizards
The Bale bot SHALL support expiring multi-step sessions for customer, lead, opportunity, interaction, follow-up, search, stage, quote/order/payment, and report workflows. Draft wizard data SHALL remain outside operational tables until final confirmation. `/لغو` SHALL discard the session. Every update and callback SHALL be replay-protected so duplicate delivery applies at most one write.

#### Scenario: Wizard is cancelled
- **WHEN** a user starts a new-lead wizard and sends `/لغو` before confirmation
- **THEN** the session is cleared and no partial lead or customer is created

#### Scenario: Callback is replayed
- **WHEN** Bale delivers the same confirmed callback twice
- **THEN** the operation is applied once and the second delivery returns the existing result

### Requirement: Sensitive Bale Actions Require Confirmation and Domain Validation
Financial actions, final won/lost transitions, customer merge, and order fulfillment actions initiated through Bale SHALL present a summary and require explicit confirmation. They SHALL call the same backend domain services as the website and SHALL return validation blockers without bypassing risk, payment, stock, quote, or logistics rules.

#### Scenario: Payment action has a blocker
- **WHEN** a Bale operator tries to confirm an invalid or incomplete payment action
- **THEN** the bot reports the domain blocker and neither order nor opportunity state changes

### Requirement: Public Price Bot Is Isolated from Internal CRM
Unbound/public Bale users MAY continue to query the live product catalog, but public messages SHALL NOT expose CRM records, internal commands, customer balances, leads, opportunities, or reports. Internal command routing SHALL occur only after verified identity and permission checks.

#### Scenario: Public user asks for a customer
- **WHEN** an unbound user sends an internal customer-search command
- **THEN** the bot refuses CRM access and does not disclose whether the customer exists

### Requirement: Bale Button Navigation and Explicit Access Feedback
The Bale bot SHALL expose an inline button menu for bound operators covering today's work, both funnels, open site opportunities, customer lookup help, debtors, and public product search. Opportunity rows SHALL be selectable through callback buttons. An unbound user who invokes an internal command or button SHALL receive an explicit denial containing their Bale user id and SHALL only receive public-safe buttons. Slash-command menu registration SHALL be best-effort and MUST NOT invalidate a successfully registered webhook when Bale does not support that API method.

#### Scenario: Bound operator opens the button menu
- **WHEN** a bound operator sends `/menu` or selects the home button
- **THEN** the bot returns CRM navigation buttons authorized by the operator's live website role

#### Scenario: Operator opens an opportunity from buttons
- **WHEN** a bound operator selects an opportunity from the open-opportunities menu
- **THEN** the bot returns that live website opportunity card with back and home buttons

#### Scenario: Unbound user attempts an internal report
- **WHEN** an unbound user sends `/قیف` or selects an internal callback
- **THEN** the bot returns no CRM data, explains that the website binding is missing, shows the sender's Bale user id, and limits the keyboard to public-safe actions

#### Scenario: Bale rejects command-menu registration
- **WHEN** webhook registration succeeds but `setMyCommands` is unsupported or fails
- **THEN** the webhook remains connected and `/menu` continues to expose the inline button menu
