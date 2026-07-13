## ADDED Requirements

### Requirement: Configurable Long-Running SEO Requests

The SEO assistant SHALL use an assistant-specific provider timeout that an admin can configure from 30 through 110 seconds and that defaults to 90 seconds. Increasing this timeout SHALL NOT increase timeout values for messaging providers or unrelated AI features. Provider timeout failures SHALL identify the configured wait duration in the admin-facing error.

#### Scenario: Slow AvalAI response succeeds within the configured window

- **WHEN** the SEO assistant provider responds after 30 seconds but before its configured timeout
- **THEN** the request remains active and the response is processed normally

#### Scenario: Configured timeout expires

- **WHEN** the provider does not respond within the configured SEO assistant timeout
- **THEN** the run becomes failed and the admin receives an actionable timeout message

### Requirement: Cancellable And Idempotent SEO Chat Runs

Every SEO chat submission SHALL have a UUID request identity and a persistent lifecycle state. While a request is running, the admin SHALL be able to stop waiting immediately and submit an idempotent cancellation command. A cancelled run SHALL NOT persist its partial or late messages, SHALL NOT start additional tool/model steps after cancellation is observed, and SHALL NOT be replayed if the original POST arrives after the cancellation marker. Reusing a completed request UUID SHALL return its stored result without another provider call.

#### Scenario: Admin stops a running audit

- **WHEN** the admin selects stop while an SEO audit is processing
- **THEN** the browser request is aborted immediately, the backend run becomes cancelled, and no late answer is added to conversation history

#### Scenario: Cancellation arrives before chat creation

- **WHEN** a cancellation command for a request UUID reaches the backend before the matching chat POST
- **THEN** the cancellation marker is retained and the later chat POST does not call the AI provider

#### Scenario: Completed request is retried

- **WHEN** the same admin retries a completed request UUID
- **THEN** the stored response is returned and the provider is not called again
