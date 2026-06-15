## ADDED Requirements

### Requirement: Admin-Managed Assistant Knowledge
Admins SHALL teach the sales assistant by adding knowledge entries of two kinds — question/answer pairs and free-form articles — each with a topic and tags, and SHALL be able to edit, deactivate, or delete them. The system SHALL embed active knowledge for semantic retrieval and SHALL track staleness so changed entries can be re-embedded on demand. Only the relevant top-ranked knowledge SHALL be injected into the model prompt per query.

#### Scenario: Add and use a training
- **WHEN** an admin adds an active knowledge entry and rebuilds embeddings
- **THEN** a related user question retrieves that entry and the assistant answers using it

#### Scenario: Retrieval without embeddings
- **WHEN** embeddings are unavailable (no key/offline)
- **THEN** the assistant falls back to keyword matching over active knowledge rather than failing

### Requirement: Sales Assistant Chat With Tools
The website SHALL provide a public chat assistant that, when enabled, answers in Persian using the admin persona, sales workflow, and knowledge, and SHALL use tools to act on real store data: searching products, quoting a product's price (including roll weight for coils), and capturing a sales lead (name/phone/interest). The assistant SHALL NOT invent prices and SHALL route to human contact when it cannot help. Conversations and captured leads SHALL be recorded for the admin to review.

#### Scenario: Product and price answer
- **WHEN** a visitor asks for a product (e.g., ورق ST52) and its price
- **THEN** the assistant searches the catalog, returns matching products with links, and quotes the price from real offers (not invented)

#### Scenario: Lead capture
- **WHEN** a visitor signals intent to buy and provides name and phone
- **THEN** the assistant records the lead, marks the conversation as a lead, and it appears in the admin conversations/leads view

#### Scenario: Disabled or unconfigured
- **WHEN** the assistant is disabled, or no LLM key/endpoint is configured
- **THEN** the public widget is hidden (disabled) or returns a graceful message directing the visitor to human contact, without crashing
