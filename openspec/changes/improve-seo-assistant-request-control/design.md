## Context

The SEO chat endpoint is synchronous. A single user action may perform an embedding request, a chat completion, a page audit, and another chat completion. The previous 30-second timeout was shared with unrelated integrations and could not be safely increased globally.

## Decisions

### SEO-specific configurable timeout

Store `request_timeout_seconds` on the SEO assistant singleton. Default to 90 seconds and validate 30–110 seconds. This leaves operational margin below the proxied domain's 120-second Cloudflare read limit. Only AvalAI/OpenAI-compatible requests made by the SEO assistant use this value; page fetching and messaging providers keep their existing shorter limits.

Reference: <https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/>

### Persistent request identity

Create `SeoChatRequest`, keyed by a client-generated UUID. It records owner, conversation, lifecycle status, cancellation flag, reply/error, and completion time. Reusing a completed request ID returns the stored result instead of charging for a duplicate model call.

### Cooperative backend cancellation

The frontend aborts its fetch for immediate user feedback and separately calls `POST /api/seo-assistant/admin/chat/{request_id}/cancel/`. The cancel endpoint is idempotent and can create a cancellation marker before the original POST arrives. AI orchestration checks cancellation before and after provider calls and around every tool step. Messages linked to a cancelled request are deleted so late results do not enter history.

An OpenAI-compatible provider has no portable cancellation API. If cancellation happens while a blocking provider read is already in progress, the upstream computation may continue until that read returns or times out; the application still discards its result and performs no later tool/model step.

## Failure handling

- Invalid request UUID: HTTP 400.
- Duplicate running UUID: HTTP 409.
- UUID owned by another admin: HTTP 404.
- Provider timeout/error: request becomes `failed` and the actionable provider message is returned.
- Cancellation endpoint unavailable: browser wait still stops immediately and the UI reports that server-side cancellation could not be confirmed.
