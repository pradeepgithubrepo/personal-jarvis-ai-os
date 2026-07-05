# Jarvis V1 — Supabase Schema Audit

> Migration Knowledge Base · Document 04  
> Produced: 2026-07-04 · Source: `sql/recreate_all_supabase_tables.sql`, `storage/models/`, `docs/JARVIS_ARCHITECTURAL_ANCHOR.md`

---

## Overview

The Supabase database uses a custom schema: `jarvis_insights_schema`. All tables live within this schema. The SQLite local database mirrors most of these tables for runtime caching.

This audit covers every table in the current DDL, its purpose, which services write to it, which consume it, and whether it should be preserved or removed for V2.

---

## Signal Pipeline Tables

### `signals`

| Field | Detail |
|-------|--------|
| **Purpose** | Stores structured, unified signals parsed from mobile and email sources |
| **Key Columns** | `id`, `source`, `signal_type`, `category`, `importance`, `summary`, `raw_json`, `created_at`, `message_id` |
| **Referenced By** | Qualification Agent reads; Streamlit dashboard; Android sync |
| **Records Count** | Unknown — accumulated from all signal sources |
| **Still Used?** | Yes — though the modular pipeline has largely superseded this with `qualified_signals` and `understood_signals` |
| **Preserve?** | Yes |
| **Remove?** | No |

**Note:** This table represents the original pre-modular architecture's "final" signal store. In the modular architecture, the equivalent is `understood_signals`. The `signals` table remains for legacy consumers. V2 should clarify whether this table is the source of truth or `understood_signals`.

---

### `mobile_signals`

| Field | Detail |
|-------|--------|
| **Purpose** | Stores raw incoming signals from the Android device before any processing |
| **Key Columns** | `id`, `device_id`, `source`, `sender`, `message`, `mobile_timestamp`, `processed`, `created_at`, `message_hash` |
| **Referenced By** | ConsumerService (write), Qualification Agent (read) |
| **Records Count** | All raw signals ever ingested |
| **Still Used?** | Yes — primary ingestion table |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `qualified_signals`

| Field | Detail |
|-------|--------|
| **Purpose** | Stores qualification results (QUALIFIED/REVIEW/REJECTED) for every processed raw signal |
| **Key Columns** | `id`, `signal_id`, `source`, `sender`, `message`, `timestamp`, `qualification_score`, `qualification_status`, `qualification_reason`, `created_at` |
| **Referenced By** | Qualification Agent (write), Signal Understanding Agent (read) |
| **Records Count** | All qualified signals |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `understood_signals`

| Field | Detail |
|-------|--------|
| **Purpose** | Stores canonical signal contracts produced by the Signal Understanding Agent |
| **Key Columns** | `id`, `qualified_signal_id`, `raw_signal_id`, `signal_type`, `importance`, `confidence`, `summary`, `reason`, `processing_path`, `llm_model_used`, `contract_json`, `is_verified`, `created_at` |
| **Referenced By** | SUA (write), Financial Agent, Todo Agent, FYI Agent, Fact Agent (read) |
| **Records Count** | All understood signals |
| **Still Used?** | Yes — central to the modular pipeline |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Financial Tables

### `financial_events`

| Field | Detail |
|-------|--------|
| **Purpose** | Stores raw financial events extracted from signals (one per monetary signal) |
| **Key Columns** | `id`, `title`, `amount`, `currency`, `transaction_type`, `payment_channel`, `paid_to`, `paid_from`, `transaction_id`, `event_date`, `source_signal_id`, `created_at`, `category` |
| **Referenced By** | Financial Agent (write), Aggregation Service (read), Android sync |
| **Records Count** | All financial events ever processed |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `financial_facts`

| Field | Detail |
|-------|--------|
| **Purpose** | Typed, enriched ledger records — the authoritative financial fact store with full signal lineage |
| **Key Columns** | `id`, `fact_type`, `financial_event_id`, `understood_signal_id`, `qualified_signal_id`, `amount`, `currency`, `merchant_raw`, `merchant_canonical`, `merchant_id`, `category`, `classification_confidence`, `classification_method`, `event_date`, `month`, `is_excluded_from_accounting_spend`, `is_excluded_from_lifestyle_spend`, `exclusion_reason`, `refund_of_fact_id`, `is_refunded`, `refund_applied_to_month`, `salary_source_id`, `transfer_pair_id`, `created_at` |
| **Referenced By** | Financial Agent (write), Aggregation Service (read), Daily Brief Agent (read) |
| **Records Count** | One per processed financial signal |
| **Still Used?** | Yes — the most important financial table |
| **Preserve?** | Yes |
| **Remove?** | No |

**Note:** `fact_type` values: EXPENSE_EVENT, INCOME_SALARY, INCOME_UNCLASSIFIED, INTERNAL_TRANSFER, INSURANCE_PAYMENT, INVESTMENT_EVENT, REFUND_EVENT, BILL_PAYMENT_CC.

---

### `salary_events`

| Field | Detail |
|-------|--------|
| **Purpose** | Records confirmed salary credit events detected by the 4-tier salary algorithm |
| **Key Columns** | `id`, `financial_event_id`, `salary_source_id`, `detected_employer`, `gross_amount`, `currency`, `salary_month`, `detection_method`, `confidence`, `detected_at` |
| **Referenced By** | Financial Agent (write), Aggregation Service, Daily Brief Agent (read) |
| **Records Count** | One per salary credit detected |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `salary_sources`

| Field | Detail |
|-------|--------|
| **Purpose** | Known employer registry — aliases, expected pay day, expected amount, detection history |
| **Key Columns** | `id`, `canonical_name`, `aliases`, `employment_type`, `expected_day_of_month`, `day_tolerance`, `expected_amount`, `amount_tolerance_pct`, `source_bank_aliases`, `is_active`, `pending_review`, `first_detected`, `last_seen`, `detection_history`, `created_at`, `updated_at` |
| **Referenced By** | Financial Agent (read/write for Tier 2 detection) |
| **Records Count** | Zero at launch — grows from Tier 3 candidate promotions |
| **Still Used?** | Yes — but not yet created in Supabase (Technical Debt TD-5) |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `merchants`

| Field | Detail |
|-------|--------|
| **Purpose** | Canonical merchant registry — known merchants with category assignments |
| **Key Columns** | `id`, `canonical_name`, `category`, `aliases`, `logo_url`, `is_trusted`, `is_seed`, `created_at`, `updated_at` |
| **Referenced By** | Financial Agent (write), Financial Classifier (read) |
| **Records Count** | 24+ from seed list |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `merchant_profiles`

| Field | Detail |
|-------|--------|
| **Purpose** | Per-merchant spend history — lifetime spend, average transaction value, visit frequency |
| **Key Columns** | `id`, `merchant_id`, `lifetime_spend`, `avg_transaction_value`, `total_transaction_count`, `visit_count_last_30d`, `visit_count_last_90d`, `last_transaction_date`, `last_transaction_amount`, `updated_at` |
| **Referenced By** | Financial Agent (write), Daily Brief Agent (read) |
| **Records Count** | One per known merchant |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `bank_accounts`

| Field | Detail |
|-------|--------|
| **Purpose** | Known user bank account registry — used for internal transfer detection |
| **Key Columns** | `id`, `bank_name`, `ifsc_prefix`, `account_number_masked`, `account_type`, `sender_aliases`, `receiver_aliases`, `is_active`, `registered_at`, `updated_at` |
| **Referenced By** | Financial Agent (read/write for transfer detection) |
| **Records Count** | One per known user account |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `transfer_pairs`

| Field | Detail |
|-------|--------|
| **Purpose** | Links matched debit+credit legs of detected internal transfers |
| **Key Columns** | `id`, `debit_event_id`, `credit_event_id`, `amount`, `currency`, `transfer_type`, `window_seconds`, `confidence`, `detected_at` |
| **Referenced By** | Financial Agent (write), Aggregation Service (read) |
| **Records Count** | One per detected transfer pair |
| **Still Used?** | Yes — but not yet created in Supabase (Technical Debt TD-4) |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Aggregation Tables

### `monthly_spending_summary`

| Field | Detail |
|-------|--------|
| **Purpose** | Monthly rollup of all financial activity — the primary financial summary view |
| **Key Columns** | `summary_id`, `month_key`, `total_spend`, `transaction_count`, `created_at`, `updated_at`, `total_debits`, `total_credits`, `accounting_spend`, `lifestyle_spend`, `total_income`, `net_cash_flow`, `internal_transfers`, `insurance_premiums`, `investments`, `refund_offsets` |
| **Referenced By** | Aggregation Service (write), Daily Brief Agent (read), Streamlit UI, Android sync |
| **Records Count** | One per calendar month with activity |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `monthly_category_spend`

| Field | Detail |
|-------|--------|
| **Purpose** | Per-category monthly spend breakdown |
| **Key Columns** | `entry_id`, `month_key`, `category_name`, `amount`, `transaction_count`, `created_at` |
| **Referenced By** | Aggregation Service (write), Daily Brief Agent, Streamlit UI |
| **Records Count** | One per (month, category) pair |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `monthly_category_trends`

| Field | Detail |
|-------|--------|
| **Purpose** | Month-on-month percentage change per category |
| **Key Columns** | `trend_id`, `month_key`, `category_name`, `current_amount`, `previous_amount`, `change_percentage`, `created_at` |
| **Referenced By** | Aggregation Service (write), Streamlit UI |
| **Records Count** | One per (month, category) pair after first two months |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Action Tables

### `todo_items`

| Field | Detail |
|-------|--------|
| **Purpose** | Actionable task items created from ACTION class contracts |
| **Key Columns** | `todo_id`, `title`, `description`, `category`, `priority`, `status`, `due_date`, `source_agent`, `source_reference`, `confidence`, `created_at`, `updated_at` |
| **Referenced By** | Todo Agent (write), Daily Brief Agent (read), Android sync |
| **Records Count** | All active and completed todos |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

**Note:** `status` values: OPEN, COMPLETED, SNOOZED, DISMISSED. Categories: BILL, FINANCIAL, FAMILY, PERSONAL, WORK.

---

### `fyi_events`

| Field | Detail |
|-------|--------|
| **Purpose** | Informational events for user awareness — delivery updates, school circulars, travel confirmations |
| **Key Columns** | `event_id`, `event_type`, `category`, `title`, `description`, `importance`, `status`, `source_signal_id`, `duplicate_count`, `created_at`, `updated_at` |
| **Referenced By** | FYI Agent (write), Daily Brief Agent (read), Android sync |
| **Records Count** | All informational events |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Memory Tables

### `facts`

| Field | Detail |
|-------|--------|
| **Purpose** | Long-lived personal facts about the user's world — employers, policies, doctors, subscriptions |
| **Key Columns** | `fact_id`, `fact_type`, `fact_value`, `confidence`, `status`, `owner_agent`, `source_agent`, `source_type`, `first_seen`, `last_seen`, `evidence`, `created_at`, `updated_at` |
| **Referenced By** | Fact Agent (write), Daily Brief Agent (read), Streamlit UI |
| **Records Count** | Accumulated personal facts |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

### `fact_relationships`

| Field | Detail |
|-------|--------|
| **Purpose** | Links related facts (e.g., person → employer, person → insurance policy) |
| **Key Columns** | `id`, `subject_id`, `predicate`, `object_id`, `confidence`, `created_at`, `updated_at` |
| **Referenced By** | Fact Agent (write), Fact queries |
| **Records Count** | Accumulated fact links |
| **Still Used?** | Partially — relationships are created but not heavily queried |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Brief Table

### `daily_briefs`

| Field | Detail |
|-------|--------|
| **Purpose** | Stores generated Daily Briefs (morning and evening) |
| **Key Columns** | `brief_id`, `brief_type`, `generated_at`, `content`, `todo_count`, `fyi_count`, `fact_count`, `payload_json` |
| **Referenced By** | Daily Brief Agent (write), Android sync, Streamlit UI |
| **Records Count** | Two per day (morning + evening) when working |
| **Still Used?** | Yes — schema is correct; delivery to Android is the gap |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Infrastructure Tables

### `runtime_events`

| Field | Detail |
|-------|--------|
| **Purpose** | Logs system startup, shutdown, and critical runtime events |
| **Key Columns** | `id`, `event_type`, `source`, `payload`, `status`, `created_at` |
| **Referenced By** | System initializer (write), Monitoring |
| **Still Used?** | Yes |
| **Preserve?** | Yes |
| **Remove?** | No |

---

## Tables Referenced in Code But Not in DDL

These tables are referenced by `SupabaseRepo` methods but are not in the current `recreate_all_supabase_tables.sql`. This means the code silently no-ops when these tables don't exist.

| Table | Referenced By | Technical Debt |
|-------|--------------|----------------|
| `todos` | `SupabaseRepo.create_todo()` | TD-5 — different from `todo_items` (schema mismatch) |
| `salary_source` | `SupabaseRepo.fetch_salary_sources()` | TD-5 |
| `sync_audit_log` | `SyncService.log_audit()` | Not in DDL |
| `pipeline_runs` | `PipelineOrchestrator` | Not in DDL |
| `system_status` | `PipelineOrchestrator` | Not in DDL |
| `scheduler_heartbeat` | `SchedulerHeartbeatRepository` | Not in DDL |

**Observation:** There is a `todos` table referenced in the code that has a different schema from `todo_items`. The `SupabaseRepo.create_todo()` writes to a `todos` table with columns: `todo_id`, `title`, `description`, `priority`, `status`, `due_date`, `source_signal_id`. The DDL defines `todo_items` with a richer schema. This is a naming inconsistency.

---

## Minimum Schema for V2

Based on this audit, the minimum V2 schema (the tables without which the core product does not function) is:

| Table | V2 Essential? |
|-------|---------------|
| `mobile_signals` | Yes |
| `qualified_signals` | Yes |
| `understood_signals` | Yes |
| `financial_events` | Yes |
| `financial_facts` | Yes |
| `salary_events` | Yes |
| `salary_sources` | Yes |
| `merchants` | Yes |
| `bank_accounts` | Yes |
| `transfer_pairs` | Yes |
| `monthly_spending_summary` | Yes |
| `monthly_category_spend` | Yes |
| `monthly_category_trends` | Yes |
| `todo_items` | Yes |
| `fyi_events` | Yes |
| `facts` | Yes |
| `daily_briefs` | Yes |
| `runtime_events` | Yes |
| `merchant_profiles` | Optional |
| `fact_relationships` | Optional |
| `signals` (legacy) | Optional — can be retired if `understood_signals` is the primary |

Tables to create for V2 (not yet in DDL):
- `pipeline_runs`
- `system_status`
- `scheduler_heartbeat`
- `sync_audit_log`

Tables to standardise:
- Reconcile `todos` vs `todo_items` naming — pick one and remove the other

---

*Document: 04_SUPABASE_SCHEMA_AUDIT.md*  
*Part of Jarvis V1 Migration Knowledge Base*
