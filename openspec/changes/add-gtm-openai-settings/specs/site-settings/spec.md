## ADDED Requirements

### Requirement: Admin-Configurable Google Tag Manager
The system SHALL store a Google Tag Manager container ID in site settings, returned by the public `GET /api/site-settings/` as `google_tag_manager_id` and editable only by admins via `PATCH /api/site-settings/`. When set, the frontend SHALL inject the GTM container on every page; when empty, no GTM script SHALL be injected. Changing it SHALL NOT require a rebuild.

#### Scenario: Admin sets the GTM container
- **WHEN** an admin PATCHes `{"google_tag_manager_id": "GTM-XXXXXXX"}`
- **THEN** the value is persisted and returned by subsequent GETs

#### Scenario: GTM injected when configured
- **WHEN** `google_tag_manager_id` is set
- **THEN** every page loads the GTM script for that container ID

#### Scenario: No GTM when empty
- **WHEN** `google_tag_manager_id` is empty
- **THEN** no Google Tag Manager script or noscript iframe is rendered

### Requirement: Admin-Configurable OpenAI Credentials
The system SHALL store the OpenAI API key and content model in site settings, editable only by admins via `PATCH /api/site-settings/`. The public `GET /api/site-settings/` SHALL return `openai_content_model` and a boolean `openai_configured`, but SHALL NEVER return the raw `openai_api_key`. The SEO content-suggestion service SHALL use the stored key and model, falling back to the `OPENAI_API_KEY` / `OPENAI_CONTENT_MODEL` env vars when empty. The key SHALL be updated only when a non-empty value is submitted.

#### Scenario: Admin sets the OpenAI key
- **WHEN** an admin PATCHes `{"openai_api_key": "sk-..."}`
- **THEN** the key is persisted, `openai_configured` becomes `true`, and the raw key is never returned by GET

#### Scenario: Empty key submission preserves the stored key
- **WHEN** an admin PATCHes settings with an empty `openai_api_key`
- **THEN** the previously stored key is left unchanged

#### Scenario: Content generation uses configured credentials
- **WHEN** the SEO content-suggestion service runs and `openai_api_key` is set
- **THEN** it authenticates with the stored key and uses `openai_content_model` (or the env model when that is empty)

#### Scenario: Falls back to env when unset
- **WHEN** `openai_api_key` is empty
- **THEN** the service uses the `OPENAI_API_KEY` env var, and reports a clear error if that is also empty
