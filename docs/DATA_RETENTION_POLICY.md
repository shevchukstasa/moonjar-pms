# Moonjar PMS — Data Retention Policy

**Version:** 1.0
**Effective Date:** 2026-03-21
**Enforced By:** `api/retention.py` (automated monthly cleanup via APScheduler)

---

## Overview

This document defines the data retention periods for all categories of data stored in the Moonjar Production Management System. Retention periods are designed to balance operational needs, legal compliance (Indonesian regulations), and system performance.

Automated cleanup runs monthly on the 1st of each month at 03:00 UTC.

---

## Retention Schedule

| Data Category | Table(s) | Retention Period | Action After Expiry | Justification |
|---|---|---|---|---|
| **Audit Logs** | `audit_logs` | 3 years | Archive to cold storage | Legal compliance, dispute resolution |
| **Orders (completed)** | `production_orders` | 5 years | Archive | Tax/accounting requirements (Indonesia) |
| **Orders (active)** | `production_orders` | Indefinite | Keep | Operational necessity |
| **Material Transactions** | `material_transactions` | 3 years | Archive | Inventory audit trail |
| **Quality Inspections** | `quality_checks`, `defect_records` | 5 years | Archive | Product liability |
| **Production Logs** | `batches`, `schedule_slots` | 3 years | Archive | Process improvement |
| **User Activity** | `security_audit_log`, `active_sessions` | 1 year | Delete | Privacy |
| **Rate Limit Events** | `rate_limit_events` | 30 days | Delete | Security monitoring |
| **Notifications (read)** | `notifications` (is_read=true) | 90 days | Delete | UX cleanup |
| **Notifications (unread)** | `notifications` (is_read=false) | 1 year | Delete | Ensure delivery |
| **AI Chat History** | `ai_chat_history` | 6 months | Delete | Privacy |
| **RAG Embeddings** | `rag_embeddings` | Rebuild on demand | Delete old (>1y) | Technical optimization |
| **Kiln Inspection Results** | `kiln_inspections`, `kiln_inspection_results` | 5 years | Archive | Safety compliance |
| **Reconciliation Logs** | `inventory_reconciliations`, `stage_reconciliation_logs` | 3 years | Archive | Financial audit |
| **TPS Metrics** | `tps_shift_metrics`, `tps_deviations` | 2 years | Archive | Performance analysis |
| **Daily Task Distributions** | `daily_task_distributions` | 1 year | Delete | Operational |
| **Photos** | `position_photos`, `order_packing_photos`, `worker_media` | 2 years | Archive | Product records |
| **Kiln Calculation Logs** | `kiln_calculation_logs` | 2 years | Delete | Technical optimization |
| **Backup Logs** | `backup_logs` | 1 year | Delete | Monitoring |

---

## Indonesian Legal Requirements

The following legal requirements inform the retention periods above:

### Tax Records (UU Perpajakan)
- **Retention:** 10 years per Indonesian tax law
- **Applies to:** Financial entries (`financial_entries`, `order_financials`), completed orders, material transactions
- **Note:** The 5-year retention for completed orders is the minimum automated period. Financial records with tax implications should be archived (not deleted) and kept for 10 years in cold storage.

### Employment Records
- **Retention:** 2 years after employee termination
- **Applies to:** User accounts (`users`), user activity logs
- **Note:** Deactivated user records are never auto-deleted. The 1-year deletion of `security_audit_log` applies only to session/login tracking, not to employment records.

### Product Liability
- **Retention:** 5 years (general statute of limitations)
- **Applies to:** Quality checks, defect records, kiln inspections, production batches
- **Note:** These are archived, not deleted, to support potential liability claims.

---

## Automated vs. Manual Actions

### Automated (api/retention.py)
The following cleanups run automatically on the 1st of each month:
- Rate limit events (>30 days)
- Read notifications (>90 days)
- Unread notifications (>1 year)
- AI chat history (>6 months)
- Daily task distributions (>1 year)
- Stale active sessions (>30 days expired)
- Security audit log (>1 year)
- Backup logs (>1 year)
- RAG embeddings (>1 year)
- Worker media (>2 years)
- Kiln calculation logs (>2 years)

### Manual / Future (requires archive infrastructure)
The following require S3/cold storage archive infrastructure before automation:
- Audit logs archival (>3 years)
- Completed orders archival (>5 years)
- Material transactions archival (>3 years)
- Quality data archival (>5 years)
- Production logs archival (>3 years)
- Photos archival (>2 years)

---

## Archive Strategy

When archive infrastructure (S3 cold storage) is available:

1. **Export** records to JSONL format, grouped by table and month
2. **Upload** to S3 bucket with lifecycle policy (Glacier after 30 days)
3. **Delete** from primary database after successful upload verification
4. **Log** archival action in `audit_logs`

S3 lifecycle policy:
- Standard storage: 30 days (for potential rollback)
- Glacier Instant Retrieval: 30 days to 1 year
- Glacier Deep Archive: 1 year to end of retention

---

## Monitoring

- Monthly cleanup results are logged at INFO level in `moonjar.retention`
- Failed cleanups are logged at ERROR level
- The health endpoint reports last retention cleanup status (future enhancement)

---

## Policy Changes

Any changes to this policy must be:
1. Reviewed for legal compliance (Indonesian tax and labor law)
2. Updated in this document
3. Updated in `api/retention.py`
4. Deployed and verified
