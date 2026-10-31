## ADDED Requirements
### Requirement: Recurring channel posts
Messaging administrators SHALL manage plain-text daily schedules with Tehran time, selected weekdays, Bale/Telegram destinations, preview and history. Global and per-row switches default off. Disabled morning example includes current Jalali date.
#### Scenario: Duplicate daily run
- **WHEN** a due enabled schedule is processed repeatedly or edited after reservation
- **THEN** unique schedule/date snapshot sends at most once per platform; stopped/unknown sends never retry automatically.
#### Scenario: Missed or disabled schedule
- **WHEN** now is outside the 30-minute window or master/row is disabled
- **THEN** no new send occurs and past days are not replayed.
### Requirement: Explicit OTP delivery choice
Customers SHALL choose configured Bale or SMS for login, phone binding and guest inquiry. Bale uses native Safir OTP; no silent fallback. Existing expiry, attempt limit, ownership and shared phone/IP budget remain. Secrets/codes SHALL not appear in logs.
#### Scenario: Bale only
- **WHEN** selected enabled Bale is configured while SMS is off
- **THEN** native OTP is sent and verified without SMS; logged-in inquiry remains OTP-free.
#### Scenario: Disabled or unknown channel
- **WHEN** a disabled/unsupported method is requested or pending Bale is disabled before verify
- **THEN** no provider call/credential issuance occurs.
