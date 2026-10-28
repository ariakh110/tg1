## ADDED Requirements

### Requirement: Verified purchase owner notification
One committed phone-verified purchase inquiry SHALL create one persistent owner notice. Rollback, invalid codes and repeated verification SHALL NOT create additional notices. Authorized assistant administrators SHALL see unread notices in the existing site bell and mark them read independently per user.

#### Scenario: Two administrators
- **WHEN** one administrator reads a notice
- **THEN** another administrator retains their unread state and the inquiry status remains unchanged

### Requirement: Private Bale delivery with recorded outcomes
A minute background worker SHALL send bounded reference/contact/item summaries only to configured private admin Bale bot destinations. Site notice persistence SHALL be independent of provider success. Sending attempts SHALL be claimed before network calls and uncertain/stale outcomes SHALL NOT automatically resend.

#### Scenario: Worker crash after dispatch starts
- **WHEN** an attempt remains sending past its timeout
- **THEN** it becomes unknown and a later task does not automatically repeat it

#### Scenario: Missing Bale configuration
- **WHEN** a verified inquiry commits without a configured Bale admin bot
- **THEN** the site notice exists with explicit configuration status and no external message is sent
