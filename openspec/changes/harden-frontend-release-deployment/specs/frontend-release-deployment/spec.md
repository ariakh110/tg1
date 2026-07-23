## ADDED Requirements

### Requirement: Deterministic Frontend Dependencies
Every frontend production release SHALL install the exact dependency graph from the committed lockfile before running the production build.

#### Scenario: Release introduces a new package
- **WHEN** `package.json` and `package-lock.json` include a dependency that is absent from the currently deployed `node_modules`
- **THEN** the deployment SHALL install that dependency in the staged release before invoking the build.

#### Scenario: Frontend archive is incomplete
- **WHEN** a generated frontend archive lacks the manifest, lockfile, or versioned deployment helper
- **THEN** the local deployment wrapper SHALL reject the archive before uploading it.

#### Scenario: Operator prepares files for manual upload
- **WHEN** the operator selects prepare-only mode
- **THEN** the wrapper SHALL build and validate the requested committed archives, refresh the server updater, and SHALL NOT open an SCP or SSH connection.

#### Scenario: Windows Git archive converts shell line endings
- **WHEN** a generated frontend archive contains a carriage return in the deployment helper
- **THEN** the local wrapper SHALL reject the archive before upload and identify the invalid line endings.

#### Scenario: Staged helper contains legacy CRLF
- **WHEN** the Linux updater extracts a helper with CRLF line endings
- **THEN** it SHALL remove trailing carriage returns before asking Bash to execute the helper.

### Requirement: Isolated Frontend Build And Activation
The deployment SHALL install and build a frontend release outside the active frontend directory and SHALL activate it only after both operations succeed.

#### Scenario: Dependency installation fails
- **WHEN** lockfile installation exits unsuccessfully
- **THEN** the active source, dependencies, build output, and running service SHALL remain unchanged.

#### Scenario: Production build fails
- **WHEN** the staged production build exits unsuccessfully
- **THEN** the active `.next` output SHALL remain unchanged and the staged release SHALL NOT be activated.

#### Scenario: Staged build succeeds
- **WHEN** dependency installation and production build both succeed
- **THEN** the deployment SHALL replace the stable frontend path with the complete staged release before restarting the service.

### Requirement: Frontend Release Configuration Preservation
The deployment SHALL copy supported production environment and npm configuration files from the active release into staging without adding those files to the source archive.

#### Scenario: Production environment file exists
- **WHEN** the active release contains a supported `.env` variant or `.npmrc`
- **THEN** the staged build and activated release SHALL receive the same file and file mode.

### Requirement: Frontend Activation Rollback
The deployment SHALL restore the previous complete frontend release when the newly activated service cannot restart or does not become active.

#### Scenario: New frontend service restart fails
- **WHEN** systemd cannot restart the service after the directory swap
- **THEN** the deployment SHALL restore the previous directory and attempt to restart the previous release.

#### Scenario: New frontend becomes active
- **WHEN** systemd confirms that the new service is active
- **THEN** the deployment SHALL remove the temporary previous-release directory.
