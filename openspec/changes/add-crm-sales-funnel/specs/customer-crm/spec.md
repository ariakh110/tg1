## MODIFIED Requirements

### Requirement: Customer Sales Stage and Source
Each CRM customer SHALL carry a sales `stage` drawn from the B2B funnel — سرنخ (`new`) → پرورش/اعتمادسازی (`nurturing`) → پیش‌فاکتور (`proposal`) → مذاکره/قرارداد (`negotiation`) → مشتری فعال (`won`) → وفادار (`loyal`), plus ازدست‌رفته (`lost`) — and a lead `source` covering both walk‑in/phone and B2B channels (تماس ورودی، معرفی، سایت، اینستاگرام، مراجعه حضوری، دستیار، لینکدین، نمایشگاه، انجمن/سندیکا، پلتفرم B2B، تماس سرد، بازاریابی میدانی، سایر), both stored as stable ASCII codes with Persian display labels. New customers SHALL default to the «سرنخ» (`new`) stage. Admins SHALL be able to set and change both, and SHALL be able to filter the customer list by stage and by source.

#### Scenario: Stage defaults to the first funnel step and can advance
- **WHEN** an admin creates a customer without specifying a stage
- **THEN** the customer's stage is «سرنخ» (`new`)
- **AND** the admin can later advance it to «پیش‌فاکتور» (`proposal`) and the change persists

#### Scenario: Filter the funnel by stage
- **WHEN** an admin filters customers by stage «مذاکره/قرارداد» (`negotiation`)
- **THEN** only customers currently in that stage are returned

## ADDED Requirements

### Requirement: Stage Change History
When a customer's sales stage changes through the admin CRM API, the system SHALL automatically record the transition on the customer's activity timeline as a distinct «تغییر مرحله» entry that captures the previous stage, the new stage, the time, and the acting admin. Such an entry SHALL NOT schedule a follow‑up and SHALL NOT appear on the follow‑ups dashboard. These transition records SHALL be queryable to measure how customers move through the funnel over time.

#### Scenario: Advancing a stage is logged with from/to
- **WHEN** an admin changes a customer's stage from «سرنخ» to «پیش‌فاکتور»
- **THEN** a «تغییر مرحله» activity appears on that customer's timeline recording from=سرنخ, to=پیش‌فاکتور, the time, and the admin
- **AND** it does not create or appear as an open follow‑up

#### Scenario: Setting the same stage does not log
- **WHEN** an admin saves a customer without changing the stage value
- **THEN** no «تغییر مرحله» activity is created

### Requirement: Sales Funnel and KPI Dashboard
The system SHALL provide an admin‑only funnel summary across all customers, giving the count of customers at each funnel stage, an overall conversion rate (customers won ÷ all customers), business KPIs derived from the ledger (total sales, total outstanding receivable, and an average‑purchase CLV proxy), the number of customers created in the current month, and the count of open follow‑ups. When sufficient stage‑change history exists, it SHALL also report the average sales‑cycle length (time from creation to reaching «مشتری فعال») and the quote→close ratio (customers that ever reached «مشتری فعال» ÷ customers that ever reached «پیش‌فاکتور»); when history is insufficient these time‑based KPIs SHALL be reported as unavailable rather than as zero.

#### Scenario: Funnel reflects the current distribution
- **WHEN** customers exist across several stages and an admin opens the funnel dashboard
- **THEN** each stage shows its current customer count and the conversion rate is computed from those counts

#### Scenario: Ledger KPIs come from transactions
- **WHEN** customers have recorded purchases and payments
- **THEN** the dashboard reports total sales as the sum of purchases and the total outstanding as the sum of positive balances

#### Scenario: Time-based KPIs need history
- **WHEN** no customer has yet reached «مشتری فعال» through a logged stage change
- **THEN** the average sales‑cycle length and quote→close ratio are reported as unavailable («—»), not as zero

### Requirement: Admin-only Funnel Access
The funnel summary endpoint SHALL be accessible only to admin users (staff/superuser or an active admin role), consistent with the rest of the CRM, and SHALL NOT be exposed to public or ordinary authenticated users.

#### Scenario: Non-admin is denied the funnel
- **WHEN** an unauthenticated or non‑admin user requests the funnel endpoint
- **THEN** the request is denied
