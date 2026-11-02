## MODIFIED Requirements
### Requirement: Steel chain public scope
The page SHALL show only steel-chain groups in every public trade projection, excluding cement and nonferrous commodities while retaining database history.
#### Scenario: Cement exists in storage
- WHEN a user requests summary, list or symbol history
- THEN cement is excluded from rows, group/date metadata and map.
## ADDED Requirements
### Requirement: Official periodic steel board
The system SHALL store validated MarketId1 TTS snapshots separately from final trades and expose them without upstream calls on public requests.
#### Scenario: Provider failure
- WHEN the refresh fails
- THEN the previous snapshot is retained and a failure/staleness notice is shown.
#### Scenario: Session date unavailable
- WHEN the source provides no trading date
- THEN receive time is labelled as receive time and no session date is invented.
### Requirement: Distinct seller and final prices
The UI SHALL default to steel-board offers and provide a separate reported-trades tab.
#### Scenario: User views an offer
- WHEN an offer shows CurrentSellPrice
- THEN it is labelled seller price with original currency, without implying a completed trade.
