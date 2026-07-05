# Schema Reconciliation Report

**Date:** 2026-06-28  
**Sprint:** Local ↔ Supabase Database Consolidation  

---

## 1. Schema Comparison Matrix

| Table | Local Count | Supabase Count | Status | Key Differences / Issues |
| :--- | :---: | :---: | :--- | :--- |
| `signals` | 100 | 5 | **DRIFT** | Column structures differ (SQLite integer key vs remote UUID key). |
| `mobile_signals` | 337 | 0 | **MISSING** | Missing entirely on remote. |
| `qualified_signals` | 437 | 0 | **MISSING** | Missing entirely on remote. |
| `understood_signals` | 224 | 224 | **MATCH** | Aligned. |
| `financial_facts` | 61 | 0 | **MISSING** | Missing entirely on remote. |
| `financial_events` | 80 | 5 | **MATCH** | Aligned. |
| `transfer_pairs` | 17 | 0 | **MISSING** | Missing entirely on remote. |
| `salary_sources` | 6 | 0 | **MISSING** | Missing entirely on remote. |
| `salary_events` | 6 | 0 | **MISSING** | Missing entirely on remote. |
| `merchants` | 30 | 0 | **MISSING** | Missing entirely on remote. |
| `merchant_profiles` | 3 | 0 | **MISSING** | Missing entirely on remote. |
| `bank_accounts` | 4 | 0 | **MISSING** | Missing entirely on remote. |
| `runtime_events` | 71 | 0 | **MISSING** | Missing entirely on remote. |
| `facts` | 8 | 8 | **MATCH** | Aligned. |
| `fact_relationships` | 0 | 0 | **MATCH** | Aligned. |
| `todo_items` | 4 | 4 | **MATCH** | Aligned. |
| `fyi_events` | 67 | 67 | **MATCH** | Aligned. |
| `daily_briefs` | 4 | 4 | **MATCH** | Aligned. |
| `monthly_spending_summary` | 3 | 0 | **MATCH** | Table exists on remote but contains no records. |
| `monthly_category_spend` | 9 | 0 | **MATCH** | Table exists on remote but contains no records. |
| `monthly_category_trends` | 9 | 0 | **MATCH** | Table exists on remote but contains no records. |

---

## 2. MISSING REMOTE TABLES

> [!IMPORTANT]
> The following tables exist locally in SQLite but are **MISSING** from the remote Supabase PostgreSQL database:
>
> 1. `mobile_signals`
> 2. `qualified_signals`
> 3. `financial_facts`
> 4. `transfer_pairs`
> 5. `salary_sources`
> 6. `salary_events`
> 7. `merchants`
> 8. `merchant_profiles`
> 9. `bank_accounts`
> 10. `runtime_events`

*Please execute the schema alignment script on the remote console to create these tables before proceeding to the data migration phase.*
