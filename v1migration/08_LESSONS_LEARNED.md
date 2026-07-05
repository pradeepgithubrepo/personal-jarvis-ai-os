# Jarvis V1 — Lessons Learned

> Migration Knowledge Base · Document 08  
> Produced: 2026-07-04 · Source: Full V1 codebase analysis, architectural anchor document, DAILY_BRIEF_AUDIT.md, ANDROID_CODEBASE_ASSESSMENT.md

---

## Overview

This document captures every significant lesson learned from building and running Jarvis V1. These lessons are drawn from code analysis, documented architectural decisions, validation records, and identified failure patterns. Each lesson includes a category tag, the evidence that produced it, and the implication for V2.

These lessons are ordered by severity and impact, not chronology.

---

## ARCHITECTURE LESSONS

---

### A-1: Dead Code Kills Confidence

**Lesson:** Leaving deprecated code in the codebase alongside its replacement makes it impossible to know which path is active.

**Evidence:**
- `services/daily_brief_generator.py` is deprecated, crashes on execution, and still exists
- `services/supabase_sync_service.py` is deprecated, crashes on execution, and still exists
- `services/signal_processor.py` (28KB monolithic pipeline) still exists alongside the new modular pipeline
- `services/financial_intelligence.py` is not aligned to the V2 model but has not been removed

The presence of four broken or obsolete files creates ambiguity about what actually runs. A developer reading the codebase cannot determine the actual execution path without tracing the orchestrator call chain.

**V2 Implication:** Delete deprecated code at the point of replacement. Do not archive — delete. If version history is needed, it lives in git.

---

### A-2: One Owner Per Table is the Right Constraint

**Lesson:** The `AD-3: One Owner Per Table` architectural decision eliminated an entire class of bugs.

**Evidence:** The V1 monolithic pipeline (`signal_processor.py`) mixed financial event writing, todo creation, and FYI storage in a single class. This caused:
- Cannot re-run aggregation without re-running classification
- A bug in aggregation logic could corrupt fact records
- Impossible to determine which writer caused a data issue

The modular architecture with strict ownership eliminated all three problems. Each agent owns its tables exclusively.

**V2 Implication:** Maintain this constraint strictly. If a new agent needs to write data, it gets its own table. Shared tables are prohibited.

---

### A-3: The Canonical Contract is the Right Interface

**Lesson:** Having a single, typed JSON contract between Signal Understanding and all downstream agents (rather than passing raw message strings) eliminated an entire class of parsing bugs.

**Evidence:**
- In the old pipeline, every agent independently parsed the raw message for amounts, merchants, and dates
- Different agents used different regex patterns, producing inconsistent results
- Amounts parsed as ₹450.5 by one agent and as ₹450 by another
- The canonical contract (with `entities.monetary_value.amount` as a typed float) made this class of bug impossible

**V2 Implication:** The contract interface is locked. No downstream agent should ever receive or parse a raw message string.

---

### A-4: Mock Code Left in Production is Invisible

**Lesson:** A test scaffolding mock that was never removed from `pipeline_orchestrator.py` means the entire production pipeline runs on mocked LLM responses.

**Evidence:**
- `services/pipeline_orchestrator.py` contains `_instrumented_ask` — a function that intercepts `IntelligenceRouter.ask` and replaces it with a mock response
- This was a testing artifact from development validation
- It was never removed
- The result: any pipeline run through the orchestrator uses fake LLM classification, not the real model

**V2 Implication:** Testing scaffolding must never be committed to production code. Test mocks belong in `tests/`. If they're in `services/`, they will eventually be called in production.

---

### A-5: Shadow Mode Validation is Essential

**Lesson:** Every module that ran in shadow mode before going live produced better results than modules that didn't.

**Evidence (from Anchor Document Section 11):**
- The Qualification Agent ran in shadow mode against ~300 real signals. It caught 2 false positives in promotional rejection before going live.
- The Signal Understanding Agent ran in shadow mode. It caught 3 of 6 semantic errors (insurance renewals incorrectly routed to FinancialAgent, bill alerts incorrectly routed, missing `_calculate_business_confidence()` method)
- Modules that skipped shadow validation (daily brief, consumer scheduling) have more production failures

**V2 Implication:** Every new agent must have a shadow validation step before replacing its predecessor. A module that is not validated is not complete.

---

### A-6: Real Data Reveals Edge Cases Synthetic Data Misses

**Lesson:** Indian bank SMS formats, WhatsApp group messages, and IMAP email parsing have real-world variety that no synthetic test data can replicate.

**Evidence (from Anchor Document Section 8.1):**
- Multi-line bank SMS: "Received!\nINR 2,500" — newline broke the keyword match for "received inr" in the SUA deterministic path
- This was only discovered when running against `scratch/dump_preview.json` (real production signals)
- The fix (`re.sub(r'\s+', ' ', msg_lower)`) normalised whitespace before matching
- This specific bug would never appear in synthetic test data

**V2 Implication:** Validation must always use real production signals. Synthetic data is not sufficient for qualifying pipeline changes.

---

## PRODUCT LESSONS

---

### P-1: The Daily Brief is the Most Important Feature — And the Most Neglected

**Lesson:** The Daily Brief is the single most valuable output. Everything else in the system is a means to this end. Yet the Daily Brief has received less investment than the financial classification algorithms.

**Evidence:**
- Financial intelligence has sophisticated algorithms: 4-condition transfer detection, 4-tier salary detection, refund-as-offset semantics, Accounting/Lifestyle spend split
- The Daily Brief cannot even reliably reach the user (no API endpoint, Android displays local template)
- Two competing implementations exist (DailyBriefAgent and deprecated DailyBriefGenerator)

**V2 Implication:** The Daily Brief must be treated as the primary product deliverable. All other features exist to serve the brief. Fix the brief end-to-end before adding any other features.

---

### P-2: Too Many Screens Means No Screen is Used

**Lesson:** The Android app has 11 screens. Users engage with at most 3. The 5 category screens (Family, School, Travel, Health, Shopping) are nearly identical code and are rarely opened.

**Evidence:**
- `FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt` display filtered subsets of FYI events
- They are largely duplicate code (same composable structure, different filter parameters)
- The information they show is also available in the unified FYI screen with a category filter

**V2 Implication:** Fewer screens, better used. Collapse to 4 core screens: Home (brief), Todos, Finance, Capture. Add category filters to the FYI screen. Remove dedicated category screens.

---

### P-3: Voice Capture is Not a V2 Feature — It's a V2 Requirement

**Lesson:** Without voice capture, Jarvis is purely reactive. It only processes what the network delivers automatically. A user cannot ask Jarvis to remember something, schedule something, or capture a thought. This is the single biggest user experience gap.

**Evidence:**
- Current capture mechanisms are all passive: SMS reading, notification interception
- If the user thinks "I need to call the doctor today", there is no way to capture this thought in Jarvis
- The product vision explicitly mentions "personal AI assistant" but without voice input, it cannot assist — it can only report

**V2 Implication:** Voice capture must be built as a core feature, not added later. The capture screen should be accessible via a floating action button from every screen. Wake-word detection is a V3+ concern — a tap-to-speak button is sufficient for V2.

---

### P-4: Spouse Adoption Unlocks the System's Full Value

**Lesson:** A family intelligence system that tracks only one family member sees half the picture. Shobana's transactions, appointments, and school-related signals are all invisible.

**Evidence:**
- Supabase sync only contains signals from the primary user's device
- Shobana has no Jarvis interface
- Family financial picture is incomplete (split households often have expenses on both members' cards)
- School-related WhatsApp groups that Shobana monitors are not captured

**V2 Implication:** Spouse support must be designed into V2 from day one. This means:
1. A way for Shobana to install the Android app and authenticate
2. Signal upload identifies the device/user
3. Brief content can include signals from both family members
4. Todos created from Shobana's signals are shared with Pradeep

---

### P-5: Financial Data Honesty Builds Trust

**Lesson:** The system presents spending data as if it is complete. It is not. Wallet spend, credit card underlying transactions, and cash transactions are invisible. Presenting incomplete data without labelling it as such is misleading.

**Evidence:**
- Wallet top-ups (GPay Lite funding) appear as debits in the system but the actual wallet spend is invisible
- Credit card bills appear as `BILL_PAYMENT_CC` but the merchant breakdown of what drove the card bill is unknown
- Monthly "lifestyle spend" is understated for users who heavily use wallets or credit cards

**V2 Implication:** The brief should include an explicit "visibility scope" statement: "Your spending visibility this month: Bank SMS (100%), Credit card detail (0%), Wallet spend (0%)." Users can make better decisions when they know what the data represents.

---

### P-6: Operational Reliability is a Feature

**Lesson:** A feature that works 80% of the time is not a feature — it is a source of frustration. The consumer sync running only once per server lifecycle is an example of a reliability gap that makes the system feel broken.

**Evidence:**
- Consumer sync runs once at server startup — signals accumulate until the next restart
- The scheduler does not schedule `run_consumer_sync` as a recurring job
- Daily Brief scheduler jobs fire at 06:00 and 20:00 but depend on the server surviving uninterrupted between restarts

**V2 Implication:** Every recurring operation must have a recurring schedule. Every pipeline step must be observable (logged, tracked, alerted on failure). The system must be able to recover from a server restart without manual intervention.

---

### P-7: Freshness is Non-Negotiable for Briefs

**Lesson:** A Daily Brief from yesterday is not a Daily Brief — it is an archive entry. The brief must reflect the state of the world as of this morning to be valuable.

**Evidence:**
- InsightSyncWorker runs once per day at 06:20
- If a financial transaction arrives at 10:00 AM, it won't appear in the brief until the next morning
- If the server was down at 06:00, no morning brief is generated at all

**V2 Implication:** Brief generation must have a retry mechanism. If the 06:00 brief generation fails, it must retry at 06:05, 06:10, etc. Brief delivery must be verified — if the Android app did not receive the brief, the system should know.

---

## TECHNICAL LESSONS

---

### T-1: Idempotency Must Be Designed In, Not Retrofitted

**Lesson:** The modules that were designed with idempotency from the start (AggregationService, SignalQualificationAgent) are the most reliable. The modules that were not designed with idempotency (daily_brief_generator, consumer sync) are the most unreliable.

**Evidence:**
- `AggregationService.run_for_month()` clears rollup tables before rebuilding — safe to run any number of times
- `SignalQualificationAgent` checks for existing records before inserting — safe to re-run
- The legacy `DailyBriefGenerator` re-creates briefs without checking for duplicates — multiple runs create multiple entries

**V2 Implication:** Every agent must implement idempotency before being considered complete. The check is: "If I run this agent twice on the same data, is the output identical?"

---

### T-2: Config in JSON Files Must Migrate to Database

**Lesson:** User-specific configuration stored in JSON files (`config/user_context.json`, `config/family_context.json`) cannot be updated without server access. This makes the system inflexible and requires technical knowledge to change.

**Evidence:**
- To update Shobana's phone number, someone must edit `config/family_context.json` on the server
- To add a new merchant mapping, someone must edit `config/jarvis_rules.json`
- To change notification preferences, there is no UI

**V2 Implication:** All user-specific configuration should live in Supabase tables (with a management UI) rather than JSON files. JSON files are acceptable for system-level rules (qualification thresholds, base noise filters) but not for personal data.

---

### T-3: SQLite as Runtime Cache — Not Source of Truth

**Lesson:** The architectural decision (`AD-9: Supabase Is the Source of Truth, AD-10: SQLite Is the Runtime Cache`) is correct and was vindicated by observed failure patterns.

**Evidence:**
- When SQLite was corrupted in a development session, the data could be rebuilt from Supabase
- The sync pipeline proved that Supabase is reliably accessible from both the server and the Android app
- SQLite provides fast local access during pipeline execution without network dependency

**V2 Implication:** Maintain this constraint. SQLite is for runtime speed. Supabase is for permanence. This means: every record written to SQLite must eventually be written to Supabase. The sync must be auditable.

---

### T-4: Test Mocks Must Be Explicitly Scoped

**Lesson:** The monkey-patching of `IntelligenceRouter.ask` in `pipeline_orchestrator.py` is the most dangerous production bug in V1. It means the entire pipeline runs on mocked LLM responses without anyone knowing.

**Evidence:**
```python
# In pipeline_orchestrator.py (production code):
original_ask = IntelligenceRouter.ask

def _instrumented_ask(self, prompt, context=None, task_type=None, ...):
    # MOCK: Returns fake response instead of calling real LLM
    mock_response = '{"signal_type": "unknown", ...}'
    return mock_response, usage

IntelligenceRouter.ask = _instrumented_ask  # Monkey-patches the REAL method
```

This code runs in production. Every LLM call is intercepted with a mock.

**V2 Implication:** Mocks are only acceptable in test files (`tests/`). No test scaffolding in `services/`. Before V2 launch, the mock must be removed and the real LLM path verified end-to-end.

---

### T-5: Schema Migrations Must Be Atomic and Tracked

**Lesson:** The schema mismatch between `DailyBrief` model attributes (`brief_id`, `brief_type`, `generated_at`) and legacy references (`date`, `content_json`, `sync_status`) caused production crashes that persisted across multiple sessions without being noticed.

**Evidence:**
- `daily_brief_generator.py` references `DailyBrief.date` which does not exist
- `supabase_sync_service.py` references the same nonexistent attributes
- The system crashed silently — the brief was never generated but no alert was raised

**V2 Implication:** Every schema change must be accompanied by a migration that updates all code that references the changed table. Schema changes and code changes must be deployed together. Use alembic for SQLite migrations. Use Supabase migrations for remote schema.

---

### T-6: LLM Classification Cache Prevents Repeated API Calls

**Lesson:** The `classification_cache` table (SHA-256 hash of input → cached LLM response) is a simple but effective optimisation. It prevents the LLM from being called with the same text twice.

**Evidence:**
- Financial classification for "ZOMATO INTERNET" will always produce FOOD_DINING
- Without caching, every Zomato transaction triggers an LLM call
- With caching, only the first Zomato transaction triggers an LLM call; all subsequent ones hit the cache

**V2 Implication:** Preserve the classification cache. Extend it to SUA contracts (cache entire contract by message hash, not just category). This reduces LLM calls by 60–80% for returning merchants.

---

### T-7: Pre-Seeded Registries Are Mandatory for First-Run Quality

**Lesson:** The experience of the first pipeline run with no merchant data is universally bad. Starting with a pre-seeded registry of 24 merchants (from `FinancialClassifier.MERCHANT_SEED`) produced meaningful classifications from the first run.

**Evidence (from Anchor Document AD-12):**
- An empty registry on first run produces 100% EXPENSE_UNCLASSIFIED — useless
- The 24-merchant seed list ensures meaningful classification from day one
- After the first month, the dynamic learning layer begins to add more merchants

**V2 Implication:** Every registry (merchant, salary source, bank accounts) must be pre-seeded with sensible defaults for the user. The onboarding experience should also include a one-time historical review to seed registries from prior transaction history.

---

### T-8: The Financial Preservation Override is the Right Safety Net

**Lesson:** The qualification agent's financial preservation override — which upgrades a near-rejected financial signal from REJECTED to REVIEW — prevented real financial events from being silently dropped.

**Evidence:**
- Without this override, a promotional-sounding message like "Congratulations! ₹2,500 has been credited to your account" would be rejected as PROMOTION
- With the override, the financial keyword "credited to your account" triggers the preservation rule
- The signal is sent to REVIEW rather than being silently discarded

**V2 Implication:** Preserve this override. It is the most important safety net in the qualification pipeline. It ensures no real money movement is silently lost.

---

### T-9: Scheduling Must Be Observable

**Lesson:** The scheduler (`JarvisScheduler`) has jobs but provides no visibility into whether they fired, whether they succeeded, or whether they failed. The only observable is the SQLite `scheduler_heartbeat` table — but this was added as technical debt, not as the primary monitoring mechanism.

**Evidence:**
- `run_consumer_sync` is never added to the scheduler but no error is raised
- If the morning brief job fails, there is no alert
- The heartbeat fires every 30 seconds but records only that the process is alive, not that pipeline stages completed

**V2 Implication:** Every scheduled job must write a run record on start and on completion (with status, duration, and any errors). If a job fails, it should log the failure to `pipeline_runs` and optionally trigger a retry. Monitoring should be observable from the dashboard.

---

## Summary Table

| Lesson | Category | Severity | V2 Action Required |
|--------|----------|----------|-------------------|
| A-1: Dead code kills confidence | Architecture | HIGH | Remove all deprecated code immediately |
| A-2: One owner per table | Architecture | MEDIUM | Maintain existing constraint |
| A-3: Canonical contract is correct | Architecture | LOW | Maintain existing design |
| A-4: Mocks in production | Architecture | CRITICAL | Remove `_instrumented_ask` mock |
| A-5: Shadow mode validation | Architecture | HIGH | Require shadow validation for every new agent |
| A-6: Real data required | Architecture | HIGH | Validate only with real signals |
| P-1: Brief is primary product | Product | CRITICAL | Fix brief end-to-end first |
| P-2: Too many screens | Product | MEDIUM | Collapse to 4 core screens |
| P-3: Voice capture is required | Product | HIGH | Build as V2 core feature |
| P-4: Spouse adoption | Product | HIGH | Design multi-user from V2 day one |
| P-5: Financial data honesty | Product | MEDIUM | Label visibility scope explicitly |
| P-6: Reliability is a feature | Product | HIGH | All recurring ops must have recurring schedules |
| P-7: Brief freshness | Product | HIGH | Add retry mechanism and delivery verification |
| T-1: Idempotency | Technical | HIGH | Enforce idempotency per agent |
| T-2: Config in files | Technical | MEDIUM | Migrate to Supabase tables |
| T-3: SQLite vs Supabase | Technical | LOW | Maintain existing constraint |
| T-4: Test mocks in production | Technical | CRITICAL | Remove mock before any production use |
| T-5: Schema migrations | Technical | HIGH | Atomic migrations, track all schema changes |
| T-6: LLM classification cache | Technical | LOW | Preserve and extend |
| T-7: Pre-seeded registries | Technical | MEDIUM | Seed all registries at launch |
| T-8: Financial preservation override | Technical | HIGH | Preserve this safety net |
| T-9: Scheduling observability | Technical | HIGH | Write run records per scheduled job |

---

*Document: 08_LESSONS_LEARNED.md*  
*Part of Jarvis V1 Migration Knowledge Base*
