# Change: Improve SEO assistant request timeout and cancellation

## Why

SEO page audits can require an embedding lookup, one or more model calls, and a live-page tool call. The current shared 30-second provider timeout is too short for AvalAI and returns a read-timeout error even when the provider is still processing. The admin UI also has no way to stop waiting or prevent a late response from being added to conversation history.

## What Changes

- Add an SEO-assistant-specific, admin-configurable provider timeout with a 90-second default and a bounded 30–110 second range.
- Give every chat submission a UUID request record with running, completed, cancelled, and failed states.
- Add an idempotent admin-only cancellation endpoint that can arrive before or during the original chat request.
- Prevent cancelled runs from continuing tool iterations or persisting partial/late messages.
- Add a frontend stop control that aborts the active browser request immediately and records cancellation in the backend.

## Impact

- Affected specs: `seo-assistant`.
- Backend: `SeoAssistantSettings`, new `SeoChatRequest`, `SeoMessage`, chat/cancel APIs, AI orchestration, migration, tests.
- Frontend: SEO assistant chat controls, API client, and timeout setting.
- Product requirements: `openspec/prd/seo-assistant-request-control-prd.md`.
- Deployment runs the new migration through the existing backend update script.
