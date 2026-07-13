## 1. Backend

- [x] 1.1 Add bounded `request_timeout_seconds` to SEO assistant settings
- [x] 1.2 Add `SeoChatRequest` lifecycle model and link generated messages to a request
- [x] 1.3 Add idempotent cancellation endpoint and duplicate-request handling
- [x] 1.4 Check cancellation around provider and tool calls and discard cancelled messages
- [x] 1.5 Add migration and Django admin visibility

## 2. Frontend

- [x] 2.1 Send a UUID and AbortSignal with each SEO chat request
- [x] 2.2 Replace the send action with a stop control while processing
- [x] 2.3 Call backend cancellation on stop and component unmount
- [x] 2.4 Expose the 30–110 second provider timeout in SEO settings

## 3. Verification

- [x] 3.1 Add backend tests for timeout bounds, idempotency, early cancellation, and message cleanup
- [x] 3.2 Run backend SEO tests, migration checks, and Django checks
- [x] 3.3 Run frontend lint/build and responsive smoke checks
- [x] 3.4 Validate this OpenSpec change in strict mode
- [x] 3.5 Commit, pull/push, and rebuild manual deploy archives
