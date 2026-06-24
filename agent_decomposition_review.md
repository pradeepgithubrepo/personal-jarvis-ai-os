# Agent Decomposition Review: Jarvis Agent-First Architecture Transition

This document reviews the current business responsibilities across the Jarvis backend components and defines their mapping to a decentralized, domain-driven **Agent-First Architecture**.

---

## 1. Step-by-Step Module Review

### Step 1: `MobileSignalPipeline`
* **Signal Loading**: Fetches unprocessed database rows from the `mobile_signals` table (`MobileSignalRepository.get_unprocessed_signals(limit=100)`).
* **Timestamp Handling**: Parses incoming string/epoch mobile timestamps into standard Python datetimes. Implements a **90-day age filter** where stale signals are discarded.
* **Noise Filtering**: Evaluates raw signals using `MobileNoiseFilter.is_noise()` to drop OTPs, deleted notifications, and WhatsApp system logs.
* **Signal Enrichment (LLM Extraction)**: Invokes `MobileIntentExtractor` to structure raw text into intent, priority, details, and categories.
* **Signal Routing & Classification**: Saves the structured results into the unified `signals` table, and conditionally creates records in `tasks`.
* **Deduplication**: Runs cross-channel deduplication before saving signals.

### Step 2: `SignalProcessor`
* **Signal Classification**: Deterministcally maps unified signals to categories (`IGNORE`, `INSURANCE`, `FINANCIAL`, `TODO`, `FYI`) via keyword and config rules.
* **Todo Extraction**: Parses signals classified as `TODO`, parses/normalizes due dates (overdue checks, NLP matchers like "tomorrow"), and writes `Todo` records to local SQLite and remote Supabase.
* **Financial Extraction**: Parses signals classified as `FINANCIAL` or `INSURANCE`, normalizes transaction amount, merchant name, and date, and writes `FinancialEvent` records to SQLite and Supabase.
* **FYI Extraction**: Identifies informational updates (shopping deliveries, travel tickets, school circulars) and writes `FyiEvent` records to SQLite and Supabase.

### Step 3: `FinancialIntelligenceService`
* **Internal Transfer Detection**: Runs chronological leg-matching (within 24 hours and equal amounts) to flag internal fund movements between user accounts, categorizing them as `INTERNAL_TRANSFER`.
* **Debit Transaction Classification**: Invokes `FinancialClassifier` to classify debit events into categories (Groceries, Dining, Rent, etc.).
* **Summary and Trend Aggregation**: Triggers category spending rollups and MoM trends.

### Step 4: `FinancialAggregator`
* **Supabase Sync and Clearing**: Re-aggregates remote Supabase records. Triggers database wipes of `monthly_category_trends`, `monthly_category_spend`, and `monthly_spending_summary` to execute a clean reconstruction.
* **Remote Aggregation**: Mirrors internal transfer detection, classifications, spending summaries, and trends on the Supabase Postgres instance.

### Step 5: `DailyBriefGenerator`
* **Inputs**: Reads `Todo`, `FinancialEvent`, and `FyiEvent` records matching the target date.
* **Compilations & Overrides**: Filters high-priority items, identifies high-value debits (>= 10,000 INR), alerts on transaction failure keywords, and extracts renewals in the next 7 days.
* **Outputs**: Returns a structured daily summary JSON payload, stores it in `DailyBrief` locally, and uploads it to Supabase via `SupabaseSyncService`.

---

## 2. Agent Ownership Matrix

The following matrix maps existing module responsibilities to future independent agents:

| Responsibility | Current Module | Future Agent Owner | Complexity | Priority |
| :--- | :--- | :--- | :--- | :--- |
| Raw signal fetch & timestamp parse | `MobileSignalPipeline` | **Signal Intake Agent** | Low | High |
| Rule-based noise filtering | `MobileSignalPipeline` | **Signal Intake Agent** | Low | High |
| Cross-channel deduplication check | `MobileSignalPipeline` | **Signal Intake Agent** | Medium | Medium |
| LLM Intent & Triage routing | `MobileSignalPipeline` | **Signal Triage Agent** | High | High |
| Deterministc signal categorizing | `SignalProcessor` | **Signal Triage Agent** | Low | High |
| Todo parsing & due-date normalizing | `SignalProcessor` | **Todo Agent** | Medium | Medium |
| FYI parsing & message summarization | `SignalProcessor` | **FYI Agent** | Low | Low |
| Financial event & amount extraction | `SignalProcessor` | **Financial Agent** | Medium | High |
| Internal transfer leg-matching | `FinancialIntelligenceService` | **Financial Agent** | High | High |
| Spending Category classification | `FinancialClassifier` | **Financial Agent** | High | High |
| Monthly rollups & MoM trend computing | `FinancialAggregator` | **Financial Agent** | Medium | Medium |
| Fact-base retrieval & extraction | None | **Fact Agent** | High | Low |
| Daily brief rollup & alert compilation | `DailyBriefGenerator` | **Daily Brief Agent** | Medium | High |

---

## 3. Data Flow Architecture

The target pipeline operates as a sequence of specialized agent hands:

```text
Consumer Ingestion Sync
      │
      ▼
Signal Intake Agent   ──(Drops noise / OTP / old signals)
      │
      ▼ (Outputs: candidate_signals)
Signal Triage Agent   ──(Classifies intent category)
      │
      ├───────────────────────┼───────────────────────┐
      ▼                       ▼                       ▼
  Todo Agent              FYI Agent            Financial Agent
  (Extracts Todos)     (Extracts FYIs)       (Extracts Expenses,
      │                       │               Internal Transfers,
      │                       │               Monthly Spend Trends)
      └───────────────────────┼───────────────────────┘
                              ▼
                      Daily Brief Agent
                      (rollup compilation)
```

---

## 4. Database Impact Matrix

| Agent | Read Tables | Write Tables | Source of Truth |
| :--- | :--- | :--- | :--- |
| **Signal Intake Agent** | `mobile_signals` (raw) | `mobile_signals` (marks processed) | SQLite / Supabase |
| **Signal Triage Agent** | `candidate_signals` | `signals` (structured), `signal_classifications` | Supabase |
| **Todo Agent** | `signals`, `tasks` | `todos` | Supabase |
| **FYI Agent** | `signals` | `fyi_events` | Supabase |
| **Financial Agent** | `signals`, `financial_events` | `financial_events`, `financial_transaction_classifications`, `monthly_spending_summary`, `monthly_category_spend`, `monthly_category_trends` | Supabase |
| **Fact Agent** | `signals` | `facts` | Supabase |
| **Daily Brief Agent** | `todos`, `financial_events`, `fyi_events` | `daily_briefs` | Supabase |

---

## 5. Success Criteria: Code Migration Map

* **What survives unchanged**:
  * Rules engine categorizations (`RulesEngine`).
  * Basic database CRUD methods (`SupabaseRepo`).
  * Local LLM router client implementations (`IntelligenceRouter`).
* **What moves**:
  * Filtering rules (`MobileNoiseFilter`) move into the **Signal Intake Agent**.
  * NLP date parsing helpers (`parse_and_normalize_due_date`) move to the **Todo Agent**.
  * Financial classification utilities (`FinancialClassifier`) move to the **Financial Agent**.
  * Rollup computations move into the **Financial Agent** and **Daily Brief Agent** packages.
* **What can be deleted**:
  * Redundant local SQLite-based aggregation pipelines in `FinancialIntelligenceService` (which duplicate the logic of `FinancialAggregator`).
  * Monolithic pipeline script hooks in `MobileSignalPipeline`.
