## ADDED Requirements

### Requirement: Canonical Domain Migration

The production application SHALL publish `https://kavehmetal.com` as its canonical origin across HTML metadata, sitemap entries, robots directives, structured data, and generated public links. Safe requests received through the origin IP, `www`, legacy domain, or another non-canonical Host SHALL permanently redirect to the new apex while preserving path and query. Unsafe methods on a non-canonical Host SHALL remain rejected.

#### Scenario: Canonical apex request
- **WHEN** a client requests a public page with Host `kavehmetal.com`
- **THEN** the application serves the page without a Host redirect
- **AND** crawler-facing URLs use `https://kavehmetal.com`

#### Scenario: Legacy deep link
- **WHEN** a safe request for `/products?family=sheet` reaches the application with Host `kavex.ir`
- **THEN** the response status is HTTP 301
- **AND** the Location is `https://kavehmetal.com/products?family=sheet`

#### Scenario: Unsafe request on a legacy Host
- **WHEN** a non-idempotent request reaches the application through a non-canonical Host
- **THEN** the request is rejected without replaying its body to the canonical origin

### Requirement: Domain-Aware Release Configuration

The manual production updater SHALL configure the backend and frontend public-domain environment keys for `kavehmetal.com` before service restart, SHALL preserve unrelated environment values and secrets, and SHALL retain one-time backups of the prior environment files.

#### Scenario: Existing production environment
- **WHEN** the release updater runs against existing backend and frontend environment files
- **THEN** only Host, CORS, CSRF, canonical site, public site, and public API URL keys are upserted
- **AND** all unrelated keys remain unchanged
- **AND** a `.pre-kavehmetal` backup is retained for each pre-existing file

#### Scenario: Post-deploy smoke validation
- **WHEN** a frontend release is activated
- **THEN** the updater verifies origin-IP and legacy-Host HTTP 301 responses
- **AND** it verifies the lowercase ST52 redirect and canonical sitemap directive
- **AND** it exits non-zero if any assertion fails

### Requirement: Persisted Integration URL Migration

Persisted Bale product-link settings and SEO assistant context values that still reference `kavex.ir` SHALL be migrated to `kavehmetal.com` without changing unrelated custom values or credentials.

#### Scenario: Legacy Bale base URL exists
- **WHEN** the domain migration is applied and the Bale base URL is an exact legacy site origin
- **THEN** it becomes `https://kavehmetal.com`
- **AND** messaging credentials and channel settings remain unchanged

#### Scenario: Customized SEO context contains legacy domain
- **WHEN** the SEO assistant context includes `kavex.ir`
- **THEN** only that domain text is replaced with `kavehmetal.com`
- **AND** the remaining customized context is preserved
