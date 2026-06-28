# Supabase Schema Audit Report

**Date:** 2026-06-28  
**Component:** Supabase V1 Schema Consolidation  
**Audit Status:** COMPLETE  

---

## 1. Overview
This audit maps and compares all local SQLAlchemy models in the SQLite database against the remote PostgreSQL tables currently defined on Supabase in `jarvis_insights_schema`.

---

## 2. Audit Matrix

| Table Name | SQLite Model (Table) | Supabase Table | Status | Key Differences / Drift |
| :--- | :--- | :--- | :--- | :--- |
| **`signals`** | `Signal` (`signals`) | `signals` | **DRIFT** | SQLite: integer `id` key. Supabase: UUID `signal_id` key, matches `save_signal` contract. |
| **`mobile_signals`** | `MobileSignal` | *None* | **MISSING** | Missing entirely on Supabase. |
| **`processed_files`** | `ProcessedFile` | `processed_files` | **MATCH** | Identical structure. |
| **`qualified_signals`** | `QualifiedSignal` | `qualified_signals` | **MATCH** | Identical structure. |
| **`understood_signals`** | `UnderstoodSignal` | `understood_signals` | **MATCH** | Identical structure. |
| **`financial_facts`** | `FinancialFact` | *None* | **MISSING** | Missing entirely on Supabase. |
| **`financial_events`** | `FinancialEvent` | `financial_events` | **MATCH** | Identical structure. |
| **`transfer_pairs`** | `TransferPair` | `transfer_pairs` | **MATCH** | Identical structure. |
| **`salary_events`** | `SalaryEvent` | *None* | **MISSING** | Missing entirely on Supabase. |
| **`salary_sources`** | `SalarySource` | *None* | **MISSING** | Missing entirely on Supabase. |
| **`merchant_profiles`** | `MerchantProfile` | *None* | **MISSING** | Missing entirely on Supabase. |
| **`facts`** | `Fact` | `facts` | **MATCH** | Consolidated V2 schema is now present and aligned. |
| **`fact_relationships`**| `FactRelationship` | `fact_relationships` | **MATCH** | Consolidated V2 schema is now present and aligned. |
| **`todo_items`** | `TodoItem` | `todo_items` | **MATCH** | Consolidated V2 schema is now present and aligned. |
| **`fyi_events`** | `FyiEvent` | `fyi_events` | **MATCH** | Consolidated V2 schema is now present and aligned. |
| **`daily_briefs`** | `DailyBrief` | `daily_briefs` | **MATCH** | Consolidated V2 schema is now present and aligned. |
| **`todos`** | *None* (Legacy) | `todos` | **LEGACY** | Deprecated legacy table, replaced by `todo_items`. |

---

## 3. Storage Ownership and Locked Module Checks

* **Qualification Agent (`qualified_signals`)**: Aligned.
* **Understanding Agent (`understood_signals`)**: Aligned.
* **Financial Agent (`financial_facts`, `financial_events`, etc.)**: Missing `financial_facts`, `salary_events`, `salary_sources`, `merchant_profiles` on remote.
* **Fact Agent (`facts`, `fact_relationships`)**: Aligned after V2 migration.
* **Todo Agent (`todo_items`)**: Aligned after V2 migration.
* **FYI Agent (`fyi_events`)**: Aligned after V2 migration.
* **Daily Brief Agent (`daily_briefs`)**: Aligned after V2 migration.
