# Jarvis V2 — Build Constitution

> Migration Knowledge Base · Document 10  
> Produced: 2026-07-04 · Source: V1 codebase analysis, lessons learned, architectural anchor document

---

## Purpose

This document is the governing rulebook for the V2 build effort. It states what every developer, engineer, or AI assistant working on V2 must know before writing a single line of code.

It is not a task list. It is not an implementation plan. It is a set of permanent constraints.

The V2 Build Constitution does not change during the V2 build period. Any proposed change to the Constitution requires explicit product owner approval.

---

## 1. The Product Principle

> **Jarvis should feel like a capable family assistant who always shows up, never misses your bills, knows your spending, remembers your school schedules, and gives you a morning summary you actually read.**

Every technical decision during V2 is evaluated against this principle. If a proposed change does not serve this principle, it does not belong in V2.

---

## 2. The Reliability Principle

> **A feature that works 80% of the time is not a feature. It is a source of frustration.**

Every pipeline step, every scheduled job, every API endpoint must be observable, retry-able, and recoverable without manual intervention. A feature is not complete until it works reliably on 30 consecutive days.

---

## 3. Locked Architectural Decisions

The following decisions are carried forward from V1 and remain locked for V2.

### AD-1: Qualification Before LLM

No signal is sent to the LLM before passing qualification. Any implementation that sends raw, unqualified signals to the LLM is architecturally incorrect.

### AD-2: Deterministic Before LLM

The deterministic path is always attempted first. LLM is only invoked when deterministic returns None. Bank SMS formats and insurance SMS formats are handled deterministically. LLM handles ambiguous signals only.

### AD-3: One Owner Per Table

Every database table has exactly one service that writes to it. No service may write to another service's table. If a new service needs to write data, it gets its own table.

### AD-4: Financial Agent Owns All Financial Tables

The Financial Agent is the sole writer to `financial_events`, `financial_facts`, `bank_accounts`, `transfer_pairs`, `salary_sources`, `salary_events`, `merchants`, `merchant_profiles`.

### AD-5: Aggregation Service Owns All Rollup Tables

AggregationService is the sole writer to `monthly_spending_summary`, `monthly_category_spend`, `monthly_category_trends`.

### AD-6: SUA Never Computes Money

The Signal Understanding Agent produces contracts. It does not compute financial totals, category rollups, or spending summaries.

### AD-7: Refunds Offset Expenses, Never Inflate Income

A confirmed refund credit reduces prior spending in the original expense month. It is never added to income.

### AD-8: Internal Transfers Are Excluded from All Spending

Both legs of an internal transfer are excluded from accounting_spend, lifestyle_spend, and income. Neither leg is counted in any spending total.

### AD-9: Supabase Is the Source of Truth

Supabase PostgreSQL is the canonical data store. SQLite is a runtime cache. All production queries against the user's data read from Supabase.

### AD-10: SQLite Is the Runtime Cache

SQLite stores intermediate pipeline state for fast local access during pipeline execution. It is not the source of truth. SQLite records can be rebuilt from Supabase if needed.

### AD-11: The FINANCIAL Class Boundary Is Inviolable

A signal receives the FINANCIAL class ONLY if money has already moved. Future obligations (bill due alerts, insurance renewal reminders, "your EMI will be deducted" notices) are NOT FINANCIAL.

### AD-12: Merchant Registry Is Pre-Seeded

The merchant registry ships with a pre-built seed list. An empty registry on first run produces 100% EXPENSE_UNCLASSIFIED, which is unacceptable.

### AD-13: AggregationService Is Idempotent

Re-running AggregationService on the same data always produces the same result. Aggregation clears rollup tables before rebuilding.

---

## 4. Build Constraints

### BC-1: No Mock Code in Production Services

No test mock, stub, or interceptor may live in any file outside `tests/`. The `_instrumented_ask` mock in `pipeline_orchestrator.py` must be removed before any V2 work begins.

Enforcement: Any code review that finds mock code in a production service must reject the change.

---

### BC-2: No Deprecated Code Alongside Its Replacement

When a component is replaced, the old component is deleted at the same commit. Not archived. Not marked deprecated. Deleted.

Specific deletions required before V2:
- `services/daily_brief_generator.py`
- `services/supabase_sync_service.py`
- `services/signal_processor.py`
- `services/financial_intelligence.py`

---

### BC-3: Every Scheduled Job Must Have a Run Record

Every recurring job must write a record to `pipeline_runs` on start and on completion (with status: STARTED, COMPLETED, FAILED; duration; signal count or relevant metric).

No silent failures. No silent completions. Every run is logged.

---

### BC-4: Every New Feature Requires a Shadow Validation

Before any new agent or pipeline stage goes live, it must run in shadow mode alongside the existing pipeline on real production signals. Shadow validation produces a written report:
- What was tested
- What passed
- What failed
- What the alignment percentage was
- What known limitations remain

A feature without a shadow validation report is not complete.

---

### BC-5: The Canonical Contract Is the Only Interface Between SUA and Downstream Agents

No downstream agent (Financial Agent, Todo Agent, FYI Agent, Fact Agent) may:
- Receive the raw message string
- Re-parse the message for amounts, merchants, or deadlines
- Derive its own classification from the raw text

The contract is the truth. The contract is the only interface.

---

### BC-6: Schema Changes Require Migration Scripts

Every change to the Supabase schema requires:
1. A migration SQL script added to `sql/migrations/`
2. The migration script is tested on a staging schema before being applied to production
3. All code that references the changed table is updated in the same commit as the migration

---

### BC-7: Config in Database, Not Files

User-specific configuration (family member names, priorities, device IDs, notification preferences) must live in Supabase `user_preferences`, not in JSON files on the server. JSON files are acceptable for system-level constants (noise filter thresholds, merchant seed lists) but not for personal user data.

Migration: Existing `config/user_context.json` and `config/family_context.json` data must be migrated to Supabase in V2. Code should fall back to JSON files only if the database is unavailable.

---

### BC-8: Voice Capture Is a First-Class Signal Source

Voice captures from the Android app are treated as first-class signals alongside SMS, WhatsApp, and email. They:
- Are assigned `source: voice_capture` in the signal schema
- Are processed by `SignalUnderstandingAgent` as ACTION or MEMORY class signals
- Are stored with full lineage (voice signal → qualified signal → understood signal → todo/fact)
- Appear in the Daily Brief as captured items

---

### BC-9: Financial Data Must Be Labelled with Visibility Scope

Any financial summary presented to the user must include a label indicating what data is included and what is excluded:

> "Based on bank SMS notifications. Credit card spend breakdown, wallet transactions, and cash purchases are not included."

This label must appear in:
- The Daily Brief financial section
- The Finance screen in the Android app
- Any financial summary on the Streamlit dashboard

---

### BC-10: No Features Unless Brief Is Working End-to-End

The Daily Brief end-to-end fix (Feature V2-01) must be complete and validated before any other V2 feature is started. The brief is the product. Everything else is supporting infrastructure.

---

## 5. Engineering Principles (From V1 — Carried Forward)

These principles from the V1 `JARVIS_ARCHITECTURAL_ANCHOR.md` remain authoritative for V2.

### P-1: LLMs Interpret. Agents Own Business Logic.

An LLM can classify a message. It cannot own the rule that says "a refund is not income." Business logic lives in code. LLMs are used for interpretation of unstructured text.

### P-2: Deterministic First

Every processing step that can be done deterministically must be done deterministically before invoking an LLM. Deterministic = 100% reproducible, zero latency, zero cost, fully testable.

### P-3: Quality Over Speed

A module that is not validated is not complete. Every module requires:
1. A validation dataset (real production data)
2. A validation script
3. A validation report

Shipping an unvalidated module is worse than shipping no module.

### P-4: One Responsibility Per Agent

Each agent does exactly one thing. The Qualification Agent qualifies. The SUA understands. The Financial Agent produces financial facts. The Aggregation Service computes rollups.

### P-5: Idempotent Pipelines

Every module must produce the same output when run twice on the same input. All writes use upsert. Rollup computations clear before rebuilding. Fact writing checks for existing records before creating new ones.

### P-6: Replayable Events

Every fact in the system traces back to the raw signal that caused it. The lineage chain is: `financial_facts` → `financial_events` → `understood_signals` → `qualified_signals` → `mobile_signals`. A fact can always be re-derived from its source signal.

### P-7: No Hidden State

Every decision made by every agent is recorded. The Qualification Agent records score and reason code. The SUA records processing path and confidence. The Financial Agent records classification method and confidence.

### P-8: No Duplicate Ownership

If two agents can write to the same table, neither owns that table. Ownership is exclusive.

### P-9: Fail Loudly, Degrade Gracefully

Supabase failures are graceful (log + continue). SQLite failures are fatal (abort the run). LLM failures produce a default safe-fallback contract. No failure silently produces wrong data.

### P-10: Real Data Only for Validation

Synthetic signals are never used for validation. Only real production signals from the actual Android device are used.

---

## 6. V2 Agent Ownership Registry

Every database table in V2 has exactly one owner. This is the authoritative registry.

### SQLite (Runtime Cache)

| Table | Owner | Reads By |
|-------|-------|---------|
| `mobile_signals` | ConsumerService | QualificationAgent |
| `qualified_signals` | QualificationAgent | SignalUnderstandingAgent |
| `understood_signals` | SignalUnderstandingAgent | FinancialAgent, TodoAgent, FyiAgent, FactAgent |
| `financial_events` | FinancialAgent | AggregationService |
| `financial_facts` | FinancialAgent | AggregationService, DailyBriefAgent |
| `bank_accounts` | FinancialAgent | FinancialAgent (transfer detection) |
| `transfer_pairs` | FinancialAgent | AggregationService |
| `salary_sources` | FinancialAgent | FinancialAgent (Tier 2 detection) |
| `salary_events` | FinancialAgent | AggregationService |
| `merchants` | FinancialAgent | FinancialClassifier |
| `merchant_profiles` | FinancialAgent | DailyBriefAgent |
| `todo_items` | TodoAgent | DailyBriefAgent, Android sync |
| `fyi_events` | FyiAgent | DailyBriefAgent, Android sync |
| `facts` | FactAgent | DailyBriefAgent, Android sync |
| `fact_relationships` | FactAgent | Fact queries |
| `daily_briefs` | DailyBriefAgent | Android sync |
| `pipeline_runs` | PipelineOrchestrator | Monitoring |
| `system_status` | PipelineOrchestrator | PipelineOrchestrator (lock) |
| `classification_cache` | FinancialClassifier | FinancialClassifier |
| `scheduler_heartbeat` | JarvisScheduler | Monitoring |
| `voice_captures` | VoiceCaptureService (V2 new) | SignalUnderstandingAgent |

### Supabase (Source of Truth)

| Table | Owner | Notes |
|-------|-------|-------|
| `mobile_signals` | ConsumerService | Raw ingestion |
| `qualified_signals` | QualificationAgent | |
| `understood_signals` | SignalUnderstandingAgent | |
| `financial_events` | FinancialAgent | |
| `financial_facts` | FinancialAgent | |
| `salary_sources` | FinancialAgent | Deploy migration |
| `salary_events` | FinancialAgent | |
| `merchants` | FinancialAgent | |
| `bank_accounts` | FinancialAgent | |
| `transfer_pairs` | FinancialAgent | Deploy migration |
| `monthly_spending_summary` | AggregationService | |
| `monthly_category_spend` | AggregationService | |
| `monthly_category_trends` | AggregationService | |
| `todo_items` | TodoAgent | Reconcile with `todos` naming |
| `fyi_events` | FyiAgent | |
| `facts` | FactAgent | |
| `fact_relationships` | FactAgent | |
| `daily_briefs` | DailyBriefAgent | |
| `pipeline_runs` | PipelineOrchestrator | Deploy migration |
| `system_status` | PipelineOrchestrator | Deploy migration |
| `user_preferences` | ConfigService (V2 new) | Family names, device IDs |

---

## 7. What Constitutes "Done" in V2

### Per-Feature Done

A feature is done when:
1. It works end-to-end on a real device with real data
2. It has been tested on 7 consecutive days without failure
3. A validation report exists documenting what was tested
4. No deprecated code was left behind
5. A run record exists in `pipeline_runs` for every automated execution

### V2 System Done

V2 is done when:
1. All 8 V2 features are complete (per Feature Done definition above)
2. All deprecated/legacy code has been removed
3. All missing Supabase tables have been created (migrations deployed)
4. The `_instrumented_ask` mock has been removed from `pipeline_orchestrator.py`
5. The system has run for 30 consecutive days without manual intervention
6. A V2 walkthrough document exists (`walkthrough.md`) documenting the full build

---

## 8. V2 Changelog — What Changed from V1

This section will be updated throughout the V2 build as changes are made.

| Date | Change | Author |
|------|--------|--------|
| — | V2 Build Constitution created | V1 migration analysis |

---

## 9. Decisions That Require Product Owner Approval

Before implementing any of the following, explicit product owner approval is required:

1. Changes to the locked architectural decisions (AD-1 through AD-13)
2. Changes to the agent ownership registry (adding or changing table ownership)
3. Changes to the canonical signal contract schema
4. Adding new signal classes beyond {FINANCIAL, INFORMATION, ACTION, ALERT, MEMORY}
5. Moving business logic between agents
6. Introducing any form of multi-writer access to any table
7. Changes to the financial boundary rule (FINANCIAL class only if money has already moved)
8. Adding any V3 features during the V2 build period

---

*Document: 10_V2_BUILD_CONSTITUTION.md*  
*Part of Jarvis V1 Migration Knowledge Base*
