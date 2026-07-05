# Reconciliation Inventory

**Date:** 2026-06-28  
**Component:** Database Reconciliation Sprint  

---

## 1. Local SQLite Inventory

| Table Name | Record Count | Primary Key | Created Date Range | Last Updated Date Range |
| :--- | :--- | :--- | :--- | :--- |
| `runtime_events` | 71 | `id` | N/A | N/A |
| `signals` | 100 | `id` | 2026-06-14 to 2026-06-14 | N/A |
| `mobile_signals` | 337 | `id` | N/A | N/A |
| `financial_events` | 80 | `financial_event_id` | N/A | N/A |
| `processed_files` | 14 | `file_id` | N/A | N/A |
| `monthly_spending_summary` | 3 | `summary_id` | N/A | N/A |
| `pipeline_runs` | 7 | `run_id` | N/A | N/A |
| `system_status` | 1 | `system_name` | N/A | N/A |
| `qualified_signals` | 437 | `id` | N/A | N/A |
| `understood_signals` | 224 | `id` | N/A | N/A |
| `bank_accounts` | 4 | `id` | N/A | N/A |
| `transfer_pairs` | 17 | `id` | N/A | N/A |
| `salary_sources` | 6 | `id` | N/A | N/A |
| `merchants` | 30 | `id` | N/A | N/A |
| `salary_events` | 6 | `id` | N/A | N/A |
| `merchant_profiles` | 3 | `id` | N/A | N/A |
| `financial_facts` | 61 | `fact_id` | N/A | N/A |
| `facts` | 8 | `fact_id` | N/A | N/A |
| `todo_items` | 4 | `todo_id` | N/A | N/A |
| `fyi_events` | 67 | `event_id` | N/A | N/A |
| `daily_briefs` | 4 | `brief_id` | N/A | N/A |
| `monthly_category_spend` | 9 | `entry_id` | N/A | N/A |
| `monthly_category_trends` | 9 | `trend_id` | N/A | N/A |

---

## 2. Remote Supabase Inventory

| Table Name | Record Count | Primary Key | Created Date Range | Last Updated Date Range |
| :--- | :--- | :--- | :--- | :--- |
| `daily_briefs` | 4 | `brief_id` | N/A | N/A |
| `fact_relationships` | 0 | `id` | N/A | N/A |
| `facts` | 8 | `fact_id` | N/A | N/A |
| `financial_events` | 5 | `financial_event_id` | N/A | N/A |
| `financial_transaction_classification` | 0 | `transaction_id` | N/A | N/A |
| `fyi_events` | 67 | `event_id` | N/A | N/A |
| `monthly_category_spend` | 0 | `entry_id` | N/A | N/A |
| `monthly_category_trends` | 0 | `trend_id` | N/A | N/A |
| `monthly_spending_summary` | 0 | `summary_id` | N/A | N/A |
| `pipeline_runs` | 5 | `run_id` | N/A | N/A |
| `processed_files` | 14 | `file_id` | N/A | N/A |
| `system_status` | 1 | `system_name` | N/A | N/A |
| `todo_items` | 4 | `todo_id` | N/A | N/A |
| `understood_signals` | 224 | `id` | N/A | N/A |
