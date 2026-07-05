# Jarvis V1 — Pipeline Audit

> Migration Knowledge Base · Document 05  
> Produced: 2026-07-04 · Source: Full codebase analysis, scheduler source, pipeline orchestrator source

---

## Overview

Jarvis V1 has a sequential multi-stage processing pipeline. This document audits every job, scheduler, and processing pipeline — their triggers, frequency, purpose, dependencies, current status, and known failure points.

---

## Scheduler Infrastructure

**Component:** `JarvisScheduler` in `orchestration/scheduler/scheduler.py`  
**Backend:** APScheduler (`BackgroundScheduler`)  
**Startup:** Launched from `app/startup.py` after system initialization

### Registered Jobs

| Job ID | Type | Schedule | Status |
|--------|------|----------|--------|
| `runtime_heartbeat` | interval | Every 30 seconds | Active |
| `morning_brief_job` | cron | Daily 06:00 | Registered but unreliable |
| `evening_brief_job` | cron | 20:00 | Registered but unreliable |

### Missing Jobs (Defined but Not Scheduled)

| Job | Method | Why Not Scheduled |
|-----|--------|-------------------|
| `run_consumer_sync` | `JarvisScheduler.run_consumer_sync()` | Method exists in the class but is never added to the scheduler via `add_job()` |

**Impact:** Consumer sync only runs once at server startup. Signals uploaded by the Android app between startup and the next server restart are never pulled automatically. This is a critical reliability gap — the system must be restarted to pick up new signals unless the scheduler is fixed.

---

## Pipeline 01 — Signal Ingestion (Consumer Sync)

| Field | Detail |
|-------|--------|
| **Trigger** | Server startup (once) |
| **Frequency** | Once per server lifecycle — NOT recurring |
| **Purpose** | Download JSON signal files from Supabase Storage `incoming/` folder, parse, deduplicate, save to `mobile_signals` SQLite |
| **Dependencies** | Supabase Storage API, `ConsumerService`, `MobileSignalRepository`, `ProcessedFileRepository` |
| **Current Status** | Working — but only runs once at startup |
| **Failure Points** | 1. Network failure during Supabase Storage download silently skips files; 2. File hash collision could skip new files with same name |
| **Reliability Assessment** | Medium — the underlying logic is correct but the scheduling is broken |

### What Works

- File SHA-256 deduplication prevents double-loading
- Files are archived after processing to prevent re-download
- Failed files are logged with `FAILED` status and moved to archive to prevent blocking

### What Doesn't Work

- Consumer sync is not a recurring job — signals accumulate in Supabase Storage until server restart
- No alerting when sync falls behind

---

## Pipeline 02 — Mobile Signal Processing

| Field | Detail |
|-------|--------|
| **Trigger** | Server startup, after consumer sync |
| **Frequency** | Once per server lifecycle |
| **Purpose** | Process unprocessed `mobile_signals` records — noise filter → LLM intent extraction → cross-channel dedup → save to `signals` table |
| **Dependencies** | `MobileSignalPipeline`, `MobileNoiseFilter`, `MobileIntentExtractor`, `IntelligenceRouter` (Ollama), `SignalRepository` |
| **Current Status** | Working |
| **Failure Points** | 1. LLM failure falls back to regex extraction; 2. Hardcoded `badminton` logic should be in rules config; 3. 90-day cutoff may discard legitimate historical signals |
| **Reliability Assessment** | Medium — correct but runs only once |

### Threads

Processes signals in a thread pool of 5 workers (`concurrent.futures.ThreadPoolExecutor`).

---

## Pipeline 03 — Email Processing

| Field | Detail |
|-------|--------|
| **Trigger** | Server startup, after mobile signal processing |
| **Frequency** | Once per server lifecycle |
| **Purpose** | Fetch unread Gmail messages, noise filter, LLM intent extraction, save to `signals` |
| **Dependencies** | `EmailPipeline`, `GmailClient`, `EmailNoiseFilter`, `EmailIntentExtractor`, Gmail OAuth credentials |
| **Current Status** | Working when Gmail credentials are valid |
| **Failure Points** | 1. OAuth token expiration causes silent failures; 2. No scheduled re-poll; 3. Gmail quota limits |
| **Reliability Assessment** | Low-medium — OAuth drift and once-only execution |

---

## Pipeline 04 — Signal Qualification

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `PipelineOrchestrator._run_pipeline_internal()` |
| **Frequency** | Per pipeline run |
| **Purpose** | Filter `mobile_signals` (unprocessed) into QUALIFIED/REVIEW/REJECTED before LLM processing |
| **Dependencies** | `SignalQualificationAgent`, `config/family_context.json`, `config/high_value_domains.json`, `config/qualification_rules.json`, `RulesEngine` |
| **Current Status** | Working |
| **Failure Points** | 1. Config files missing = all signals get base score with no context boosts; 2. Review queue has no UI |
| **Reliability Assessment** | High — deterministic, well-tested |

### Rejection Rate (Observed)

Approximately 60–70% of raw signals are rejected (OTPs, promos, noise). Approximately 20–30% are REVIEW. Approximately 10–20% are QUALIFIED.

---

## Pipeline 05 — Signal Understanding

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `PipelineOrchestrator` after qualification |
| **Frequency** | Per pipeline run |
| **Purpose** | Transform QUALIFIED signals into canonical JSON contracts |
| **Dependencies** | `SignalUnderstandingAgent`, Ollama (`qwen3:1.7b`), deterministic rule engine |
| **Current Status** | Working |
| **Failure Points** | 1. LLM model not running — all signals fail to deterministic fallback only; 2. LLM JSON parsing relies on first `{` / last `}` — malformed responses can cause errors; 3. `run_shadow_mode()` still present as dead code |
| **Reliability Assessment** | High for deterministic path; Medium for LLM path |

### Deterministic Path Coverage

The deterministic path handles:
- Bank financial transactions (debited/credited keywords + amount regex)
- Insurance payment receipts
- Insurance renewal reminders
- Bill due alerts
- Delivery updates
- Refunds (confirmed and future-tense)
- Medical appointments
- Travel bookings

Everything else falls to the LLM.

---

## Pipeline 06 — Financial Agent Processing

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `PipelineOrchestrator` for each FINANCIAL class contract |
| **Frequency** | Per signal with FINANCIAL class |
| **Purpose** | Produce `FinancialFact` records from financial contracts — transfer detection, salary detection, classification, fact writing |
| **Dependencies** | `FinancialAgent`, `FinancialClassifier`, `AggregationService`, all financial tables |
| **Current Status** | Working |
| **Failure Points** | 1. `salary_sources` table may not exist in Supabase (TD-5), silently returns empty list; 2. `transfer_pairs` Supabase table not yet created (TD-4), transfers are detected locally but not synced remotely |
| **Reliability Assessment** | High for local processing; Medium for Supabase sync of transfer pairs and salary sources |

---

## Pipeline 07 — Financial Aggregation

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `FinancialAgent` after each fact write; also called by `PipelineOrchestrator` |
| **Frequency** | Per transaction (via `AggregationService.run_for_month()`), or full sweep via `run_all()` |
| **Purpose** | Compute monthly rollups — accounting spend, lifestyle spend, income, net cashflow, category totals, MoM trends |
| **Dependencies** | `AggregationService`, `FinancialFact`, `MonthlySpendingSummary`, `MonthlyCategorySpend`, `MonthlyCategoryTrend` |
| **Current Status** | Working |
| **Failure Points** | 1. No per-signal event bus — aggregation is batch (end of pipeline run); 2. Aggregation Service and legacy `FinancialAggregator` overlap; 3. Re-aggregation clears and rebuilds — brief window where data is absent |
| **Reliability Assessment** | High — idempotent by design |

---

## Pipeline 08 — Todo Generation

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `PipelineOrchestrator` for each ACTION class contract |
| **Frequency** | Per signal with ACTION class |
| **Purpose** | Create todo items from bill alerts, appointment reminders, insurance renewals |
| **Dependencies** | `TodoAgent`, `TodoItem`, `SupabaseRepo` |
| **Current Status** | Working |
| **Failure Points** | 1. No auto-completion — payment SMS does not close the corresponding bill todo; 2. No duplicate detection across runs (same bill alert on different days creates multiple todos); 3. `SupabaseRepo` writes to `todos` table (not `todo_items`) — schema mismatch |
| **Reliability Assessment** | Medium — creates todos correctly but no lifecycle management |

---

## Pipeline 09 — FYI Generation

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `PipelineOrchestrator` for each INFORMATION class contract |
| **Frequency** | Per signal with INFORMATION class |
| **Purpose** | Record informational events for user awareness |
| **Dependencies** | `FyiAgent` (facade → `src/agents/fyi/agent.py`), `fyi_events`, `SupabaseRepo` |
| **Current Status** | Working |
| **Failure Points** | 1. No FYI grouping — same delivery package generates multiple FYIs; 2. No expiry on old FYIs |
| **Reliability Assessment** | High — simple and reliable |

---

## Pipeline 10 — Fact Extraction

| Field | Detail |
|-------|--------|
| **Trigger** | Called by `PipelineOrchestrator` for each MEMORY class contract |
| **Frequency** | Per signal with MEMORY class |
| **Purpose** | Extract and store long-lived personal facts |
| **Dependencies** | `FactAgent`, `Fact`, `FactRelationship`, `SupabaseRepo` |
| **Current Status** | Working |
| **Failure Points** | 1. MEMORY class signals are rare — may not have enough training data to validate; 2. Fact deduplication logic may produce duplicates if entity names vary |
| **Reliability Assessment** | Medium — rarely exercised |

---

## Pipeline 11 — Daily Brief Generation

| Field | Detail |
|-------|--------|
| **Trigger** | `JarvisScheduler` cron 06:00 (morning) and 20:00 (evening) |
| **Frequency** | Twice daily when scheduler is running |
| **Purpose** | Synthesise all processed data into a structured brief |
| **Dependencies** | `DailyBriefAgent` (in `src/agents/daily_brief/agent.py`), `DailyBriefBuilder`, reads from `todo_items`, `fyi_events`, `facts`, `monthly_spending_summary`, `financial_facts` |
| **Current Status** | Registered but unreliable — scheduler job exists but fails silently |
| **Failure Points** | 1. No API endpoint to deliver brief to Android; 2. Scheduler may not survive server restarts reliably; 3. Legacy `daily_brief_generator.py` crashes if called; 4. Legacy `supabase_sync_service.py` crashes if called; 5. Android app builds local template instead of consuming server brief |
| **Reliability Assessment** | Low — the most unreliable pipeline |

### Daily Brief Flow (What Should Happen)

```
06:00 cron → DailyBriefAgent.generate_morning_brief(db_session)
    → Read todo_items (OPEN, HIGH/CRITICAL priority)
    → Read fyi_events (last 24 hours, INFORMATION)
    → Read monthly_spending_summary (current month)
    → DailyBriefBuilder.build_morning_brief(todos, fyis, financial_summary)
    → DailyBriefRepository.save(brief)
    → SupabaseRepo.save_daily_brief(brief)
    → [MISSING] Push notification to Android
    → [MISSING] Android fetches brief from API
    → [MISSING] Android displays server-generated brief
```

### What Actually Happens

```
06:00 cron → DailyBriefAgent.generate_morning_brief(db_session) [maybe]
    → Brief is generated and saved to Supabase daily_briefs table [maybe]
    → No push notification sent
    → Android never fetches the brief
    → Android user wakes up to a locally-assembled template
```

---

## Pipeline 12 — Notification Delivery

| Field | Detail |
|-------|--------|
| **Trigger** | `TodoNotificationWorker` WorkManager (Android) at 07:00 and 18:00 |
| **Frequency** | Twice daily |
| **Purpose** | Push local Android notifications for todos due today or tomorrow |
| **Dependencies** | Android WorkManager, `TodoRepository`, `TodoNotificationHelper` |
| **Current Status** | Working |
| **Failure Points** | 1. Only fires for todos, not for the Daily Brief; 2. No notification if todo was completed remotely but local cache not yet refreshed |
| **Reliability Assessment** | High — local WorkManager is reliable |

---

## Android Sync Pipelines

### Signal Upload (JarvisSyncWorker)

| Field | Detail |
|-------|--------|
| **Trigger** | WorkManager |
| **Frequency** | 3x daily (05:55, 13:55, 20:55) |
| **Purpose** | Upload un-synced local signals from Android to Supabase Storage |
| **Current Status** | Working |
| **Failure Points** | 1. Network failure causes silent skip; 2. Large batch uploads may hit Supabase Storage limits |
| **Reliability Assessment** | High |

### Insight Download (InsightSyncWorker)

| Field | Detail |
|-------|--------|
| **Trigger** | WorkManager |
| **Frequency** | Daily at 06:20 |
| **Purpose** | Download todos, financial events, FYIs from Supabase REST to Android Room cache |
| **Current Status** | Working for todos/financial/FYIs — does NOT download Daily Brief |
| **Failure Points** | 1. No brief retrieval; 2. Only once per day — stale data if evening brief generated after 06:20 |
| **Reliability Assessment** | Medium — correct but incomplete |

---

## Pipeline Reliability Summary

| Pipeline | Reliability | Critical Issues |
|---------|-------------|----------------|
| Signal Ingestion (Consumer) | Medium | Runs only once; not recurring |
| Mobile Signal Processing | Medium | Runs only once |
| Email Processing | Low-Medium | OAuth drift; once-only |
| Signal Qualification | High | Well-tested; deterministic |
| Signal Understanding | High (det.) / Medium (LLM) | LLM failure graceful |
| Financial Agent | High | Missing Supabase tables for transfer pairs |
| Financial Aggregation | High | Idempotent; correct |
| Todo Generation | Medium | No lifecycle management |
| FYI Generation | High | Simple and reliable |
| Fact Extraction | Medium | Rarely exercised |
| **Daily Brief** | **Low** | **Most unreliable; delivery broken** |
| Notification Delivery | High | Local WorkManager; reliable |
| Signal Upload (Android) | High | Network-dependent but reliable |
| Insight Download (Android) | Medium | Missing brief retrieval |

---

*Document: 05_PIPELINE_AUDIT.md*  
*Part of Jarvis V1 Migration Knowledge Base*
