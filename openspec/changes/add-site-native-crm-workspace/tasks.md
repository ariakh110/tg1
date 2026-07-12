## 0. Approval and Scope

- [x] 0.1 Audit the full Persian CRM design document and all 33 workbook sheets
- [x] 0.2 Audit the existing customer CRM, direct-sales order flow, payments, logistics, assistant intake, and Bale bot
- [x] 0.3 Write the site-native CRM PRD and OpenSpec architecture
- [ ] 0.4 Product owner approves the database-as-source-of-truth, site-native funnel, phased scope, and Excel write restrictions

## 1. CRM Foundation

- [ ] 1.1 Add customer lifecycle fields and preserve/deprecate the existing customer commercial stage
- [ ] 1.2 Add `CrmLead`, source/idempotency fields, qualification state, and lead intake service
- [ ] 1.3 Add `CrmOpportunity` and opportunity stage history with owner, value, need, next action, close reason, and source link
- [ ] 1.4 Add pipeline-stage configuration and failure reasons with stable system codes
- [ ] 1.5 Add dedicated assigned follow-ups and migrate existing open activity follow-ups
- [ ] 1.6 Extend activities with opportunity, direction, result, external key, and attachment metadata
- [ ] 1.7 Add migration verification and rollback/feature-flag path

## 2. Website Event Integration

- [ ] 2.1 Make signup and assistant inquiry create idempotent leads/opportunities
- [ ] 2.2 Link each direct `StoreOrder` to exactly one CRM opportunity
- [ ] 2.3 Map quote request, quote sent/rejected/confirmed, payment, fulfillment, shipment, delivery, cancellation, and expiry events
- [ ] 2.4 Add retryable processed-event/error logging that cannot break source transactions
- [ ] 2.5 Keep marketplace/barandaz activity outside the direct-store funnel

## 3. CRM API and Admin Workspace

- [ ] 3.1 Add admin-section-scoped APIs for leads, opportunities, transitions, follow-ups, tasks, configuration, and dashboard
- [ ] 3.2 Add Lead inbox and Opportunity list/board using site-native stages
- [ ] 3.3 Upgrade customer detail with opportunities, linked site orders, timeline, follow-ups, and financial summaries
- [ ] 3.4 Replace customer-count funnel metrics with opportunity and direct-order metrics
- [ ] 3.5 Add date/owner/source/product/city filters and failure-reason reporting

## 4. Excel Round-Trip

- [ ] 4.1 Add a versioned workbook export based on the supplied 33-sheet template
- [ ] 4.2 Populate editable CRM sheets and read-only transactional projections
- [ ] 4.3 Add import preview with schema/file hash, create/update/skip/error totals, and row errors
- [ ] 4.4 Add confirmed import apply for whitelisted fields with no blank-cell deletion and full audit
- [ ] 4.5 Reject protected order/payment/product/stock/shipment edits
- [ ] 4.6 Add tests for Persian values, IDs, duplicates, stale previews, schema mismatch, and partial row errors

## 5. Bale CRM Operations

- [ ] 5.1 Add Bale-to-website-user binding and role/admin-section authorization
- [ ] 5.2 Add expiring wizard sessions and processed-update replay protection
- [ ] 5.3 Implement customer/lead/opportunity/search/note/follow-up/today/overdue commands
- [ ] 5.4 Implement safe stage/quote/order/payment/report commands through domain services
- [ ] 5.5 Add confirmation for financial/final actions, `/لغو`, timeouts, and invalid-state recovery
- [ ] 5.6 Keep public catalog price search isolated from internal CRM access

## 6. Configuration and Automation

- [ ] 6.1 Add follow-up sequences, CRM message templates, contact consent, campaigns, and task rules
- [ ] 6.2 Add typed custom field definitions/values with server validation
- [ ] 6.3 Add whitelisted automation triggers/actions, idempotency, retry, and execution audit
- [ ] 6.4 Add SLA reminders, overdue escalation, lifecycle scoring, and daily/weekly Bale reports

## 7. Verification and Deployment

- [ ] 7.1 Backend migrations/checks and focused CRM/messaging/sales/offline-payment tests pass
- [ ] 7.2 Frontend lint/build and responsive CRM workflow verification pass
- [ ] 7.3 OpenSpec strict validation passes for every implementation change
- [ ] 7.4 Deploy behind feature flags and verify counts/money/history against production before enabling
- [ ] 7.5 Verify end-to-end: site inquiry → opportunity → quote → payment → shipment → won, plus Excel and Bale replay tests
