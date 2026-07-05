# Jarvis V1 — Backend State

> Migration Knowledge Base · Document 03  
> Produced: 2026-07-04 · Source: Full codebase analysis

---

## Overview

The backend is a **Python FastAPI server** (`app/main.py`) running locally on a home server. It processes signals through a modular agent pipeline, maintains a local SQLite database as a runtime cache, and synchronises intelligence outputs to Supabase as the source of truth.

**Entry point:** `app/main.py`  
**Primary language:** Python  
**Frameworks:** FastAPI, SQLAlchemy, APScheduler, Supabase-py, Loguru, Ollama  
**LLM:** Local Ollama server (model: `qwen3:1.7b` by default)

---

## Application Layer (`app/`)

### `app/main.py`

| Field | Detail |
|-------|--------|
| **Purpose** | FastAPI application entry point — starts the web server and launches the runtime daemon thread |
| **Current Status** | Working |
| **Dependencies** | `app/startup.py`, `app/shutdown.py`, FastAPI, uvicorn |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Minor — replace daemon thread startup with proper lifecycle hooks |

---

### `app/startup.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Startup sequence: initialise system, run consumer sync, run mobile signal pipeline, run email pipeline, start scheduler |
| **Current Status** | Working |
| **Dependencies** | `system_initializer.py`, `ConsumerService`, `MobileSignalPipeline`, `EmailPipeline`, `JarvisScheduler` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — the pipeline orchestrator should be the primary driver, not startup.py |

---

## Services (`services/`)

### `services/pipeline_orchestrator.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Run the full intelligence pipeline (Consumer → Qualification → SUA → Financial → Aggregation → Todo → FYI → Fact → DailyBrief) with locking and run tracking |
| **Current Status** | Working — but `IntelligenceRouter.ask` is monkey-patched with a mock, meaning LLM calls are intercepted with a fake response in this file |
| **Dependencies** | All pipeline agents, `SupabaseRepo`, `SessionLocal` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — remove the mock `_instrumented_ask` intercept; this was a testing artifact left in production code |

**Critical Issue:** The `PipelineOrchestrator` file monkey-patches `IntelligenceRouter.ask` with a mock function at module import time. This means any pipeline run triggered through the orchestrator uses mocked LLM responses. This is a test scaffolding artifact that should not be in production.

---

### `services/signal_qualification_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Filter raw signals into QUALIFIED/REVIEW/REJECTED before any LLM processing |
| **Current Status** | Working |
| **Dependencies** | `config/family_context.json`, `config/high_value_domains.json`, `config/qualification_rules.json`, `RulesEngine` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | No |

---

### `services/signal_understanding_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Transform qualified signals into the canonical signal contract (JSON) consumed by all downstream agents |
| **Current Status** | Working |
| **Dependencies** | `IntelligenceRouter`, SQLAlchemy, `QualifiedSignal`, `UnderstoodSignal` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Minor — `run_shadow_mode()` should be removed (development artifact) |

**Design:** Deterministic path (regex + keywords) fires first. LLM only invoked when deterministic returns None. Processes ~60–80% of signals deterministically.

---

### `services/financial_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Process FINANCIAL class contracts into typed FinancialFact records — the authoritative financial ledger |
| **Current Status** | Working |
| **Dependencies** | `FinancialFact`, `FinancialEvent`, `BankAccount`, `TransferPair`, `SalarySource`, `SalaryEvent`, `Merchant`, `MerchantProfile`, `AggregationService` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | No — algorithms are locked |

**Capabilities:** 4-condition internal transfer detection, 4-tier salary detection, refund-as-offset semantics, pre-seeded merchant registry, full signal lineage.

---

### `services/financial_classifier.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Classify transactions into spend categories using merchant seed list, heuristics, rules engine, and LLM fallback |
| **Current Status** | Working |
| **Dependencies** | `RulesEngine`, `IntelligenceRouter`, `ClassificationCacheRepository` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Minor — expand merchant seed list; improve NACH/SIP detection |

**Category taxonomy (25 categories):** FOOD_DINING, GROCERIES, TRANSPORT, TRAVEL, ENTERTAINMENT, MEDICAL, SHOPPING, UTILITIES, EDUCATION, FAMILY, INSURANCE, INVESTMENT, BILL_PAYMENT, FISH, MUTTON, VEGETABLES, FUEL, INCOME_SALARY, INCOME_UNCLASSIFIED, REFUND_EVENT, INTERNAL_TRANSFER, OTHER.

---

### `services/aggregation_service.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Compute monthly rollup tables from FinancialFact records — idempotent, read-only access to facts |
| **Current Status** | Working |
| **Dependencies** | `FinancialFact`, `MonthlySpendingSummary`, `MonthlyCategorySpend`, `MonthlyCategoryTrend` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | No — idempotent and correct |

---

### `services/financial_aggregator.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Older aggregation module — contains V2 revision logic but some parts overlap with `aggregation_service.py` |
| **Current Status** | Partially superseded |
| **Dependencies** | `FinancialFact`, `SupabaseRepo` |
| **Keep?** | Partially — some functions still used |
| **Discard?** | Consolidate into `aggregation_service.py` |
| **Refactor Later?** | Yes — merge and decommission `financial_aggregator.py` |

---

### `services/financial_intelligence.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Older financial summary computation using SQLAlchemy path |
| **Current Status** | Not aligned to V2 model (old 3-condition transfer detection, single spending total) |
| **Dependencies** | SQLAlchemy, `FinancialEvent` |
| **Keep?** | No |
| **Discard?** | Yes |
| **Refactor Later?** | N/A — remove entirely |

**Technical Debt Note (TD-3):** This file predates the V2 architecture. It uses the old single-spend-total model, lacks 4-condition transfer detection, and has no salary or refund semantics.

---

### `services/todo_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Create actionable todo items from ACTION class contracts |
| **Current Status** | Working |
| **Dependencies** | `TodoItem`, `Fact`, `FinancialFact`, `SupabaseRepo` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Minor — add snooze/dismiss logic |

**Evaluation logic:** Keyword-based actionability scoring for bills, financial events, family events, personal, work. Rejection words prevent completed transactions from creating todos.

---

### `services/fact_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Extract and store long-lived personal facts from MEMORY class contracts |
| **Current Status** | Working |
| **Dependencies** | `Fact`, `FactRelationship`, `SupabaseRepo` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | No |

**Fact types managed:** PERSON, SPOUSE, CHILD, BANK_ACCOUNT, INSURANCE_POLICY, VEHICLE, PROPERTY, SUBSCRIPTION, PREFERENCE, CONTACT.

---

### `services/fyi_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Facade wrapper for FYI processing — delegates to `src/agents/fyi/agent.py` |
| **Current Status** | Working |
| **Dependencies** | `src/agents/fyi/agent.py` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — the facade pattern suggests the FYI core was recently split; consolidate |

---

### `services/daily_brief_agent.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Wrapper/reference to `src/agents/daily_brief/agent.py` |
| **Current Status** | Stub only — delegates to core agent |
| **Dependencies** | `src/agents/daily_brief/agent.py` |
| **Keep?** | Yes |
| **Discard?** | No |

---

### `services/daily_brief_generator.py` (DEPRECATED)

| Field | Detail |
|-------|--------|
| **Purpose** | Legacy daily brief generator — queries date-based financial events, todos, FYIs |
| **Current Status** | **BROKEN** — crashes immediately (references `DailyBrief.date`, `.content_json`, `.sync_status` which do not exist in the current model) |
| **Dependencies** | `SessionLocal`, `Todo`, `FinancialEvent`, `FyiEvent`, `DailyBrief` (wrong model) |
| **Keep?** | No |
| **Discard?** | Yes — immediately |
| **Refactor Later?** | N/A |

**Note:** The file is already marked `DEPRECATED` in its own docstring. It raises `RuntimeError("DailyBriefGenerator is deprecated. Use src.agents.daily_brief.agent.DailyBriefAgent instead.")`. However the file still exists and can be imported, creating confusion.

---

### `services/signal_processor.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Original monolithic classification pipeline — qualifies, classifies, extracts financial events, todos, FYIs in one class |
| **Current Status** | **LEGACY — predates the modular architecture** |
| **Dependencies** | Many — mixes qualification, classification, financial extraction, FYI extraction |
| **Keep?** | No |
| **Discard?** | Yes — decommission immediately |
| **Refactor Later?** | N/A |

**Technical Debt Note (TD-2):** This file (28KB) contains the original monolithic pipeline. It implements the old single-spend-total model, lacks the 4-condition transfer algorithm, and predates the canonical contract format. Its continued presence creates dual-path ambiguity.

---

### `services/mobile_signal_pipeline.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Process unprocessed mobile signals: noise filter, LLM intent extraction, structured signal creation |
| **Current Status** | Working |
| **Dependencies** | `MobileSignalRepository`, `MobileNoiseFilter`, `MobileIntentExtractor`, `SignalRepository` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Minor — remove 90-day cutoff for signals that pass noise filter but are recent |

**Note:** Hardcoded `badminton` downgrade logic is present — any signal mentioning badminton gets `importance = "low"`. This is a user-specific configuration that should be in `jarvis_rules.json`.

---

### `services/supabase_repo.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Data access layer for Supabase (source of truth) — all read/write operations against the remote schema |
| **Current Status** | Working |
| **Dependencies** | `supabase-py`, Supabase URL/key from settings |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — some methods reference tables that do not yet exist in Supabase (e.g., `todos`, `salary_source`) |

**Schema target:** `jarvis_insights_schema` (Supabase custom schema)

---

### `services/supabase_sync_service.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Sync daily briefs from SQLite to Supabase using the old `date`/`content_json` schema |
| **Current Status** | **BROKEN** — references model attributes that do not exist |
| **Dependencies** | `DailyBrief` (wrong schema), `SupabaseRepo` |
| **Keep?** | No |
| **Discard?** | Yes |
| **Refactor Later?** | N/A — replaced by DailyBriefAgent's built-in Supabase write |

---

### `services/aggregation_service.py` + `services/ingestion_service.py`

| Field | Detail |
|-------|--------|
| **Purpose** | `ingestion_service.py` — manages the file ingestion cycle (legacy) |
| **Current Status** | Partially superseded by ConsumerService |
| **Keep?** | Partially — review overlap with ConsumerService |
| **Refactor Later?** | Yes |

---

### `services/sync_service.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Bidirectional sync service — pushes SQLite records to Supabase for key tables with audit logging |
| **Current Status** | Working |
| **Dependencies** | SQLAlchemy, `supabase-py`, `sync_audit_log` table |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — sync should be event-driven, not bulk batch |

**Tables synced:** `mobile_signals`, `qualified_signals`, `understood_signals`, `financial_facts`, `facts`, `todo_items`, `fyi_events`, `daily_briefs`.

---

### `services/rules_engine.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Centralized rule evaluator — ignore lists, conditional ignore, merchant/VPA category mappings |
| **Current Status** | Working |
| **Dependencies** | `config/jarvis_rules.json`, `config/user_overrides.json` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Minor — hot-reload mechanism should be tested under load |

---

## Consumer Layer (`consumer/`)

### `consumer/consumer_service.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Full sync cycle — list Supabase Storage files, download, parse, deduplicate, save to SQLite, archive |
| **Current Status** | Working |
| **Dependencies** | `SupabaseClient`, `FileProcessor`, `ArchiveManager`, `MobileSignalRepository`, `ProcessedFileRepository`, `IngestionService` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — replace file-based polling with real-time push |

**Folder scanned:** `incoming/` only (consolidated from `pradeep/`, `shobana/`, `incoming/`)

---

### `consumer/supabase_client.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Supabase Storage client — list files, download blobs, move files between folders |
| **Current Status** | Working |
| **Dependencies** | `supabase-py`, settings |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | No |

---

## Intelligence Layer (`intelligence/`)

### `intelligence/routing/router.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Route LLM prompts to local (Ollama) or cloud (stub) model based on task type |
| **Current Status** | Working (local only — cloud is a stub) |
| **Dependencies** | `LocalLLM` (Ollama client), `CloudLLM` (unimplemented) |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — implement cloud LLM path (Gemini API key is configured in settings) |

---

## Orchestration Layer (`orchestration/`)

### `orchestration/scheduler/scheduler.py`

| Field | Detail |
|-------|--------|
| **Purpose** | APScheduler-based job runner for recurring pipeline tasks |
| **Current Status** | Working — heartbeat fires every 30 seconds; morning/evening brief jobs are registered |
| **Dependencies** | APScheduler, `DailyBriefAgent` |
| **Keep?** | Yes |
| **Discard?** | No |
| **Refactor Later?** | Yes — `run_consumer_sync` job is defined in the class but is NOT added to the scheduler |

**Registered jobs:**
- `runtime_heartbeat`: every 30 seconds ✅
- `morning_brief_job`: cron 06:00 ✅ (registered but may not fire if startup fails)
- `evening_brief_job`: cron 20:00 ✅ (same)

**Missing job:** `run_consumer_sync` is a static method defined in the class but is never scheduled. Consumer sync only runs once at startup.

---

## API Layer (`api/`)

### `api/routes/health.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Health check endpoint (`GET /health`) |
| **Current Status** | Working |
| **Keep?** | Yes |

### `api/routes/financial_intelligence.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Financial intelligence endpoints |
| **Current Status** | Working |
| **Keep?** | Yes |

### `api/routes/mobile_sync.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Mobile signal sync endpoint (`POST /mobile/signals`) |
| **Current Status** | Working |
| **Keep?** | Yes |

### Missing API Endpoints

| Missing Endpoint | Required For | Priority |
|------------------|-------------|---------|
| `GET /briefs/latest` | Android Daily Brief screen | CRITICAL |
| `GET /briefs/{date}` | Android brief history | HIGH |
| `GET /todos` | Direct API access (alternative to Supabase REST) | MEDIUM |
| `POST /capture/voice` | Voice capture feature | V2 |

---

## Storage Layer (`storage/`)

### Models (SQLAlchemy)

37 models covering: signals, qualified signals, understood signals, financial events, financial facts, bank accounts, merchants, merchant profiles, transfer pairs, salary sources, salary events, monthly summaries, category spend, category trends, todos, FYI events, facts, fact relationships, daily briefs, mobile signals, pipeline runs, system status, classification cache, scheduler heartbeat, and supporting types.

### Repositories

| Repository | Purpose | Status | Keep? |
|------------|---------|--------|-------|
| `signal_repository.py` | Signal CRUD | Working | Yes |
| `mobile_signal_repository.py` | Mobile signal CRUD | Working | Yes |
| `expense_repository.py` | Expense records | Working | Yes |
| `processed_file_repository.py` | File deduplication tracking | Working | Yes |
| `classification_cache_repository.py` | LLM classification cache | Working | Yes |
| `signal_repository.py` | Signal deduplication + creation | Working | Yes |
| `task_repository.py` | Task CRUD | Working | Yes |
| `runtime_event_repository.py` | Runtime event logging | Working | Yes |
| `scheduler_heartbeat_repository.py` | Scheduler monitoring | Working | Yes |

---

## Configuration

| File | Purpose | Keep? |
|------|---------|-------|
| `.env` | All secrets and settings (Supabase URL/key, Ollama URL, SQLite path) | Yes |
| `configs/settings.py` | Pydantic settings model | Yes |
| `configs/constants.py` | TaskType enum | Yes |
| `config/user_context.json` | Family names, priorities, ignore topics | Yes — move to database for V2 |
| `config/family_context.json` | Spouse/children names for qualification boost | Yes — move to database for V2 |
| `config/high_value_domains.json` | Domain keywords for qualification boost | Yes |
| `config/jarvis_rules.json` | Ignore rules, merchant/VPA category mappings | Yes |
| `config/user_overrides.json` | User transaction category overrides | Yes |
| `configs/mailbox_registry.json` | Gmail account mapping | Yes |
| `configs/google_credentials.json` | Gmail OAuth token | Yes |

---

## Summary: Backend Component Status

| Component | Status | Keep | Discard | Refactor Later |
|-----------|--------|------|---------|----------------|
| `pipeline_orchestrator.py` | Working (with mock bug) | Yes | No | Remove mock |
| `signal_qualification_agent.py` | Working | Yes | No | No |
| `signal_understanding_agent.py` | Working | Yes | No | Remove shadow mode |
| `financial_agent.py` | Working | Yes | No | No |
| `financial_classifier.py` | Working | Yes | No | Expand seed list |
| `aggregation_service.py` | Working | Yes | No | No |
| `financial_aggregator.py` | Partially superseded | Partially | Merge | Yes |
| `financial_intelligence.py` | Broken/legacy | No | Yes | N/A |
| `todo_agent.py` | Working | Yes | No | Add snooze |
| `fact_agent.py` | Working | Yes | No | No |
| `fyi_agent.py` | Working | Yes | No | Consolidate |
| `daily_brief_agent.py` | Working (facade) | Yes | No | No |
| `daily_brief_generator.py` | Broken/deprecated | No | Yes | N/A |
| `signal_processor.py` | Legacy/monolithic | No | Yes | N/A |
| `mobile_signal_pipeline.py` | Working | Yes | No | Move hardcoded rules to config |
| `supabase_repo.py` | Working | Yes | No | Fix missing tables |
| `supabase_sync_service.py` | Broken | No | Yes | N/A |
| `sync_service.py` | Working | Yes | No | Event-driven in V2 |
| `rules_engine.py` | Working | Yes | No | No |
| `consumer/consumer_service.py` | Working | Yes | No | Real-time push in V2 |
| `orchestration/scheduler.py` | Working (missing consumer sync job) | Yes | No | Add missing job |
| `intelligence/routing/router.py` | Working (cloud stub) | Yes | No | Implement cloud LLM |

---

*Document: 03_BACKEND_STATE.md*  
*Part of Jarvis V1 Migration Knowledge Base*
