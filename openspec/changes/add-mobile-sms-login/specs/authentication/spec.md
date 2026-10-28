## ADDED Requirements
### Requirement: Optional verified mobile login
The system SHALL allow mobile SMS login/signup only while enabled and configured, with single-use hashed OTP, bounded cost/attempts and no automatic legacy phone linking.
#### Scenario: New verified customer
- WHEN a new phone successfully verifies its SMS code
- THEN one ordinary account and unique verified phone identity are created and JWT returned.
#### Scenario: Disabled or replayed challenge
- WHEN the switch is off or a consumed/expired challenge is submitted
- THEN no login token is issued.
#### Scenario: Legacy phone
- WHEN an unverified profile matches a phone
- THEN the system requires existing authenticated account binding and does not grant that account access through public OTP.
#### Scenario: Admin control
- WHEN an authorized settings admin changes the switch
- THEN request and verify endpoints enforce it, while password login remains available.
