## 0. Approval and Scope

- [x] 0.1 Audit the full Persian CRM design document and all 33 workbook sheets
- [x] 0.2 Audit the existing customer CRM, direct-sales order flow, payments, logistics, assistant intake, and Bale bot
- [x] 0.3 Write the site-native CRM PRD and OpenSpec architecture
- [x] 0.4 Product owner approves both funnels, website data as primary, Bale priority, and Excel as lower priority

## 1. CRM Foundation

- [x] 1.1 Preserve the existing customer-stage funnel, endpoint, UI, and KPIs without semantic migration
- [ ] 1.2 Add `CrmLead`, source/idempotency fields, qualification state, and lead intake service
- [x] 1.3 Add `CrmOpportunity` and opportunity stage history with owner, value, need, next action, close reason, and source link
- [ ] 1.4 Add pipeline-stage configuration and failure reasons with stable system codes
- [ ] 1.5 Add dedicated assigned follow-ups and migrate existing open activity follow-ups
- [ ] 1.6 Extend activities with opportunity, direction, result, external key, and attachment metadata
- [x] 1.7 Add additive schema migration and idempotent backfill for existing direct orders and assistant inquiries
- [ ] 1.8 Add feature-flag rollout and operational rollback controls

## 2. Website Event Integration

- [ ] 2.1 Make signup and assistant inquiry create idempotent leads/opportunities
- [x] 2.2 Link each direct `StoreOrder` to exactly one CRM opportunity
- [x] 2.3 Map quote request, quote sent/rejected/confirmed, payment, fulfillment, shipment, delivery, cancellation, and expiry events
- [x] 2.4 Add retryable processed-event/error logging that cannot break source transactions
- [x] 2.5 Keep marketplace/barandaz activity outside the direct-store funnel

## 3. CRM API and Admin Workspace

- [x] 3.1 Add admin-section-scoped APIs for opportunities, transitions, synchronization audit/retry, and opportunity dashboard
- [ ] 3.2 Add the remaining Lead, dedicated follow-up/task, and CRM configuration APIs
- [x] 3.3 Add the site-native Opportunity list and second funnel view
- [ ] 3.4 Add Lead inbox and Opportunity board/drag transitions
- [x] 3.5 Include opportunities and their source/status/value in customer detail
- [ ] 3.6 Add linked transactional projections, full timeline, and financial summaries to customer detail
- [x] 3.7 Add opportunity/direct-order metrics as a second funnel without replacing customer-count metrics
- [ ] 3.8 Complete date/product/city/failure-reason filters and reporting

## 4. Bale CRM Operations

- [x] 4.1 Add Bale-to-website-user binding and role/admin-section authorization
- [ ] 4.2 Add expiring wizard sessions and processed-update replay protection
- [x] 4.3 Add read-only `/قیف`, `/فرصتها`, and `/فرصت` commands and include opportunity stages in `/امروز`
- [ ] 4.4 Implement safe stage/quote/order/payment/report commands through domain services
- [ ] 4.5 Add confirmation for financial/final actions, `/لغو`, timeouts, and invalid-state recovery
- [x] 4.6 Keep public catalog price search isolated from internal CRM access

## 5. Configuration and Automation

- [ ] 5.1 Add follow-up sequences, CRM message templates, contact consent, campaigns, and task rules
- [ ] 5.2 Add typed custom field definitions/values with server validation
- [ ] 5.3 Add whitelisted automation triggers/actions, idempotency, retry, and execution audit
- [ ] 5.4 Add SLA reminders, overdue escalation, lifecycle scoring, and daily/weekly Bale reports

## 6. Excel Round-Trip (Lower Priority)

- [ ] 6.1 Add a versioned workbook export based on the supplied 33-sheet template
- [ ] 6.2 Populate editable CRM sheets and read-only transactional projections
- [ ] 6.3 Add import preview with schema/file hash, create/update/skip/error totals, and row errors
- [ ] 6.4 Add confirmed import apply for whitelisted fields with no blank-cell deletion and full audit
- [ ] 6.5 Reject protected order/payment/product/stock/shipment edits
- [ ] 6.6 Add tests for Persian values, IDs, duplicates, stale previews, schema mismatch, and partial row errors

## 7. Verification and Deployment

- [x] 7.1 Backend migration checks and focused CRM/messaging tests pass
- [ ] 7.2 Broader sales, assistant, and offline-payment regression tests pass
- [x] 7.3 Frontend lint/build and responsive CRM workflow verification pass
- [x] 7.4 OpenSpec strict validation passes for every implementation change
- [ ] 7.5 Deploy and verify counts/money/history against production before enabling write workflows
- [ ] 7.6 Verify end-to-end: site inquiry → opportunity → quote → payment → shipment → won, plus Excel and Bale replay tests
