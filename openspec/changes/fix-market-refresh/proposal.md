# Restore daily external market updates

## Why
Production public data reports a successful sync on October 22 but still shows October 21 trades on October 24. Existing deployment does not install missing scheduled services, and public pages fetch once.

## What Changes
- Add configurable IME automatic/manual refresh and separate global automatic mode from provider availability.
- Install a five-minute systemd schedule check using existing backend environment; share database leases with Celery and manual actions.
- Show real data dates, last successful retrieval and scheduler heartbeat; select trade days and refresh open pages.

## Impact
Additive SiteSettings and MarketDataSyncState migrations, admin API and UI, public metadata. Preserve provider timestamps, historical observations and existing global provider interval. Deployment and a valid global API key remain operational requirements.
