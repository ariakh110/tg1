## ADDED Requirements

### Requirement: Customer Sales Stage and Source
Each CRM customer SHALL carry a sales `stage` (one of سرنخ / در حال پیگیری / مشتری فعال / راکد / ازدست‌رفته) and a lead `source` (one of تماس ورودی / معرفی / سایت / اینستاگرام / مراجعه حضوری / دستیار / سایر), both stored as stable ASCII codes with Persian display labels. New customers SHALL default to the «سرنخ» stage. Admins SHALL be able to set and change both, and SHALL be able to filter the customer list by stage and by source.

#### Scenario: Stage is set on creation and can change
- **WHEN** an admin creates a customer without specifying a stage
- **THEN** the customer's stage is «سرنخ»
- **AND** the admin can later change it to «مشتری فعال» and the change persists

#### Scenario: Filter the funnel by stage
- **WHEN** an admin filters customers by stage «در حال پیگیری»
- **THEN** only customers currently in that stage are returned

### Requirement: Customer Activity Timeline
The system SHALL record customer interactions as activities, each with a kind (تماس / پیام / جلسه / یادداشت), a free‑text body describing what happened, and the time it occurred. Each customer's activities SHALL be listable newest‑first, and the activity's author SHALL be captured from the requesting admin. These activity and follow‑up endpoints SHALL be accessible only to admin users (staff/superuser or an active admin role), consistent with the rest of the CRM, and SHALL NOT be exposed to public or ordinary authenticated users.

#### Scenario: Log a call and read it back
- **WHEN** an admin logs a «تماس» activity on a customer with the note «قیمت میلگرد ۱۴ را دادم»
- **THEN** the activity appears at the top of that customer's timeline with its kind, note, and time, and records which admin created it

#### Scenario: Non-admin is denied
- **WHEN** an unauthenticated or non‑admin user requests the activities or follow‑ups endpoint
- **THEN** the request is denied

### Requirement: Scheduled Follow-ups and Daily Dashboard
An activity MAY schedule a follow‑up by setting a future due date and an optional note; such a follow‑up is open until it is marked done. The system SHALL provide a dashboard of open follow‑ups across all customers, grouped into سررسیده (due before today), امروز (due today), and این هفته (due within the next seven days), each ordered by due date and carrying the customer's name and phone, plus counts per group. Marking a follow‑up done SHALL remove it from the dashboard while keeping the underlying activity on the customer's timeline. Each customer record SHALL expose its earliest open follow‑up date and its count of open follow‑ups.

#### Scenario: A scheduled callback surfaces on the dashboard
- **WHEN** an admin logs a call today and schedules a follow‑up for tomorrow
- **THEN** the follow‑up appears under «امروز» on the next day's dashboard, and under «سررسیده» if that day passes without it being done
- **AND** the customer's record reports one open follow‑up with that due date

#### Scenario: Completing a follow-up clears it but keeps history
- **WHEN** an admin marks an open follow‑up as done
- **THEN** it no longer appears on the follow‑ups dashboard and no longer counts toward the customer's open follow‑ups
- **AND** the originating activity remains visible on the customer's timeline
