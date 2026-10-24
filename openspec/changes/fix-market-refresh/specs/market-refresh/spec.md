## ADDED Requirements

### Requirement: Configurable Market Refresh
The system SHALL permit staff to select automatic or manual retrieval for IME and global metals, preserve the configured interval, and serialize scheduled and manual provider requests using an expiring database lease.

#### Scenario: Automatic mode is disabled
- **WHEN** a schedule check runs for a market in manual mode
- **THEN** it makes no provider request
- **AND** an authorized manual request can retrieve the market data

#### Scenario: One provider fails
- **WHEN** a provider request fails
- **THEN** the last successful data and success timestamp remain available
- **AND** the schedule checker still checks the other provider

### Requirement: Daily Market Transparency
The system SHALL distinguish source observation dates from successful retrieval timestamps and SHALL allow a visitor to select a stored IME trade day or an empty current day.

#### Scenario: No current-day trades exist
- **WHEN** the latest saved trade is from a previous day
- **THEN** the page identifies the real trade day and absence of current-day data
- **AND** it does not relabel historical data as current

#### Scenario: Visitor selects a trade day
- **WHEN** a trade day is selected
- **THEN** the summary, map and trade table are scoped to that date

### Requirement: Reliable Production Scheduling
The release updater SHALL install and enable an independent market schedule timer and SHALL retain shared interval and overlap protection when Celery also runs.

#### Scenario: Celery beat is not installed
- **WHEN** the release updater completes backend installation
- **THEN** a systemd timer checks market schedules every five minutes
- **AND** the admin can see the last completed check
