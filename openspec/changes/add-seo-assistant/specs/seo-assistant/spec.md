## ADDED Requirements

### Requirement: SEO Knowledge Base Ingestion And Retrieval
The system SHALL maintain an admin-managed SEO knowledge base ingested from bundled markdown (a base layer plus a 2025–2026 update layer), splitting documents into section-level chunks with a source, layer, title, and tags. The system SHALL embed active chunks for semantic retrieval and SHALL track staleness via content hash so changed chunks can be re-embedded on demand. Only the top-ranked relevant chunks SHALL be injected into the model prompt per query.

#### Scenario: Ingest the bundled knowledge base
- **WHEN** an admin runs the `ingest_seo_kb` command
- **THEN** the bundled SEO markdown is parsed into knowledge chunks (count greater than zero) and embeddings are rebuilt when an LLM key is configured

#### Scenario: Retrieval without embeddings
- **WHEN** embeddings are unavailable (no key/offline)
- **THEN** retrieval falls back to keyword matching over active knowledge rather than failing

### Requirement: Admin-Only SEO Assistant Chat
The system SHALL provide an admin-only SEO specialist chat that, when enabled, answers in Persian using the configured persona, the target-site context, and the retrieved SEO knowledge, via an OpenAI-compatible endpoint (default AvalAI) whose key is read from site settings. The assistant SHALL ground answers in the knowledge base, SHALL NOT be exposed to the public, and SHALL log conversations for admin review. The assistant SHALL be able to audit a live page through a `fetch_page_seo` tool that returns title, meta description, canonical, robots meta, headings, HTTP status, and word/link counts.

#### Scenario: Grounded SEO answer
- **WHEN** an admin asks an SEO question (e.g., title-tag length or how to optimize for AI Overviews)
- **THEN** the assistant retrieves relevant knowledge-base chunks and answers from them, citing the guidance rather than inventing it

#### Scenario: Live page audit
- **WHEN** an admin asks the assistant to audit a specific URL
- **THEN** the assistant calls `fetch_page_seo`, retrieves the page's on-page signals, and reports findings and recommendations

#### Scenario: Disabled or unconfigured
- **WHEN** the assistant is disabled, or no LLM key/endpoint is configured
- **THEN** the endpoint returns a graceful message and does not crash, and the chat is never available to non-admin users

### Requirement: Admin-Only Access Control
All SEO assistant endpoints SHALL require an authenticated admin (staff/superuser or active admin role). The assistant SHALL NOT provide any public/anonymous endpoint.

#### Scenario: Non-admin blocked
- **WHEN** an unauthenticated or non-admin user calls any SEO assistant endpoint
- **THEN** the request is rejected with an authorization error
