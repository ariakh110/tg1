## ADDED Requirements
### Requirement: Discoverable industrial trades
The system SHALL retain official physical industrial/mineral rows, including sponge iron separately and non-ferrous/cement/mineral products, exclude explicit agricultural/petrochemical rows, preserve raw source/date/unit, and never fabricate missing trades. Prior stored sponge rows SHALL be regrouped without altering official values.
#### Scenario: Sponge and non-ferrous source rows
- **WHEN** official rows include sponge iron with Persian/Arabic spacing variants, aluminum/copper and cement
- **THEN** they remain independently filterable; unrelated polyethylene/agricultural rows do not enter the industrial dataset.
### Requirement: Table-first usable filters
The page SHALL prioritize the table and labelled date/group/producer/search/trade-status controls. Reset SHALL clear all filters consistently. Default is latest stored day; all-stored-days is an explicit option. A group with no selected-day rows SHALL remain discoverable with an action to its last stored trade date.
#### Scenario: Group absent today
- **WHEN** user selects a group whose last stored record is earlier
- **THEN** current day remains honest and a labelled action opens its latest stored day without pretending it traded today.
### Requirement: Optional readable map
The map SHALL follow the table, start collapsed, use larger high-contrast labels and provide keyboard-operable text alternatives/breadcrumbs. Map scope filters exact group/producer/symbol and current date selection.
#### Scenario: Narrow map node
- **WHEN** a node is too small for readable text
- **THEN** its name is still reachable through text controls and no tiny label is required to find its trades.
