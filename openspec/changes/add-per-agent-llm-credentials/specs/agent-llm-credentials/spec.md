## ADDED Requirements

### Requirement: Per-Agent LLM API Key with Global Fallback
Each AI agent (sales assistant, SEO assistant) SHALL store its own optional `openai_api_key` in its settings. When resolving the key to call the LLM, the agent SHALL use its own key if set; otherwise it SHALL fall back to `SiteSettings.openai_api_key`, and then to the `OPENAI_API_KEY` environment variable. The raw per-agent key SHALL NEVER be returned by any GET endpoint; it SHALL be writable only by admins via the agent's settings PATCH, and an empty submission SHALL leave the stored key unchanged.

#### Scenario: Agent uses its own key when set
- **WHEN** an agent's `openai_api_key` is set
- **THEN** that agent authenticates to its LLM with its own key, independent of other agents and of the global site key

#### Scenario: Falls back to the global site key
- **WHEN** an agent's `openai_api_key` is empty but `SiteSettings.openai_api_key` is set
- **THEN** the agent authenticates with the global site key

#### Scenario: Per-agent key is never exposed
- **WHEN** the agent settings are fetched via GET
- **THEN** the response includes `api_key_configured` (boolean) but never the raw `openai_api_key`

#### Scenario: Empty submission preserves the stored key
- **WHEN** an admin PATCHes the agent settings with an empty `openai_api_key`
- **THEN** the previously stored per-agent key is left unchanged

### Requirement: AvalAI-First Base URL Defaults
The system SHALL default each agent's `openai_base_url` to an AvalAI-compatible endpoint so an Iran-hosted deployment works without manual configuration. Migrating an existing installation SHALL move the sales assistant off the stale OpenAI default only when its value is still that exact default.

#### Scenario: New installs default to AvalAI
- **WHEN** an agent's settings row is created
- **THEN** its `openai_base_url` defaults to `https://api.avalai.ir/v1`

#### Scenario: Stale OpenAI default is migrated
- **WHEN** the migration runs and the sales assistant's `openai_base_url` still equals `https://api.openai.com/v1`
- **THEN** it is updated to `https://api.avalai.ir/v1`

#### Scenario: Custom base URL is preserved
- **WHEN** the migration runs and an admin had set a non-default `openai_base_url`
- **THEN** that value is left unchanged
