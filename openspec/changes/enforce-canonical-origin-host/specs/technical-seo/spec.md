## ADDED Requirements

### Requirement: Canonical Production Host Enforcement

The production storefront SHALL serve page content only on its configured canonical Host. Safe requests made with the origin IP, `www`, or any other non-canonical Host SHALL receive an HTTP 301 redirect to the canonical HTTPS origin with the original path and query preserved. Non-idempotent requests on a non-canonical Host SHALL be rejected without replaying their body.

#### Scenario: Origin IP homepage request
- **WHEN** a client requests `/` with the production origin IP as the Host
- **THEN** the response status is HTTP 301
- **AND** the Location is `https://kavehmetal.com/`

#### Scenario: Deep link on an unexpected Host
- **WHEN** a client requests `/products?family=sheet` with `www` or an unexpected Host
- **THEN** the response status is HTTP 301
- **AND** the Location is `https://kavehmetal.com/products?family=sheet`

#### Scenario: Unsafe method on an unexpected Host
- **WHEN** a client sends a non-idempotent request with a non-canonical Host
- **THEN** the response status is HTTP 421
- **AND** the request body is not redirected to another origin

#### Scenario: Deployment regression check
- **WHEN** a frontend release is applied through the manual updater
- **THEN** the updater verifies the origin-IP Host through the local reverse proxy
- **AND** the smoke phase fails unless the canonical HTTP 301 response is observed
