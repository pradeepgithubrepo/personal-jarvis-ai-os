# Jarvis V1 — Daily Brief Audit

> Migration Knowledge Base · Document 07  
> Produced: 2026-07-04 · Source: `src/agents/daily_brief/`, `services/daily_brief_generator.py`, `orchestration/scheduler/scheduler.py`, `DAILY_BRIEF_AUDIT.md`

---

## Overview

The Daily Brief is the highest-value, most visible output of the entire Jarvis system. Every other pipeline stage — signal qualification, understanding, financial processing, todo generation, FYI extraction — feeds into the Daily Brief. If the Daily Brief works reliably, the user gets a morning summary without opening a single app. If it doesn't work, the system is invisible.

**Current state: The Daily Brief is broken.**

This is not a minor issue. It is the most critical failure in V1. This document audits the full end-to-end path — from generation to delivery — and identifies every point of failure.

---

## Architecture — What Should Exist

```
06:00 cron
    │
    ▼
DailyBriefAgent.generate_morning_brief(db_session)
    │
    ├── Read todo_items (OPEN, HIGH/CRITICAL)
    ├── Read fyi_events (last 24 hours)
    ├── Read monthly_spending_summary (current month)
    ├── Read financial_facts (recent)
    │
    ▼
DailyBriefBuilder.build_morning_brief(todos, fyis, financial_summary)
    │
    ├── Assemble structured JSON payload
    ├── Generate LLM prose (optional)
    │
    ▼
DailyBriefRepository.save(brief)  →  SQLite
    │
    ▼
SupabaseRepo.save_daily_brief(brief)  →  Supabase daily_briefs table
    │
    ▼
[MISSING] Push notification → Android
    │
    ▼
[MISSING] Android fetches GET /briefs/latest
    │
    ▼
[MISSING] Android displays server-generated brief
```

---

## Architecture — What Actually Exists

### Component 1: `src/agents/daily_brief/agent.py` — DailyBriefAgent

| Field | Detail |
|-------|--------|
| **Purpose** | Core brief generator — assembles structured morning and evening briefs |
| **Status** | Working (in isolation) |
| **Schema** | Correct — uses `brief_id`, `brief_type`, `generated_at`, `content`, `todo_count`, `fyi_count`, `fact_count`, `payload_json` |
| **Dependencies** | `DailyBriefBuilder`, `DailyBriefRepository`, `SupabaseRepo`, SQLAlchemy session |

This is the correct implementation. It reads from the right tables, produces the right output, and writes to the correct Supabase schema.

---

### Component 2: `services/daily_brief_generator.py` — DailyBriefGenerator

| Field | Detail |
|-------|--------|
| **Purpose** | Legacy brief generator — was the original implementation |
| **Status** | **BROKEN** — crashes immediately |
| **Error** | `AttributeError: 'DailyBrief' object has no attribute 'date'` |
| **Why** | References `DailyBrief.date`, `DailyBrief.content_json`, `DailyBrief.sync_status` — none of these exist in the current `DailyBrief` model |
| **Dependencies** | Wrong version of `DailyBrief` model |

The file contains its own `RuntimeError` at the start: `"DailyBriefGenerator is deprecated. Use src.agents.daily_brief.agent.DailyBriefAgent instead."` It is aware of its deprecation but it has not been removed, and its presence causes confusion about which generator is active.

---

### Component 3: `services/supabase_sync_service.py` — SupabaseSyncService

| Field | Detail |
|-------|--------|
| **Purpose** | Sync daily briefs from SQLite to Supabase using the old schema |
| **Status** | **BROKEN** — crashes on same model mismatch |
| **Error** | References `DailyBrief.date`, `DailyBrief.content_json`, `DailyBrief.sync_status` |
| **Why** | Same root cause as `daily_brief_generator.py` — outdated model references |

---

### Component 4: `orchestration/scheduler/scheduler.py` — JarvisScheduler

| Field | Detail |
|-------|--------|
| **Purpose** | Schedules `morning_brief_job` (06:00) and `evening_brief_job` (20:00) |
| **Status** | Jobs are registered correctly with APScheduler |
| **Issue** | Whether the scheduler survives a server restart reliably is unknown. If `app/startup.py` fails before reaching the scheduler start, no brief jobs ever run. |

---

### Component 5: DailyBriefScreen.kt — Android Screen

| Field | Detail |
|-------|--------|
| **Purpose** | Display the daily brief to the user |
| **Status** | **Displaying wrong content** |
| **What it does** | Assembles a local brief from the Android Room database: queries todos, financial events, FYIs locally and constructs a formatted string |
| **What it should do** | Fetch the server-generated brief from Supabase `daily_briefs` table (or a `GET /briefs/latest` API endpoint) and display it |
| **Why the mismatch** | The `InsightSyncWorker` does not pull `daily_briefs` from Supabase. No API endpoint exists for the brief. The `DailyBriefEntity` in Room is never populated with server data. |

---

### Component 6: Missing API Endpoint

| Field | Detail |
|-------|--------|
| **Required** | `GET /briefs/latest` returning the most recently generated brief JSON |
| **Current Status** | Does not exist |
| **Impact** | Android app has no way to retrieve the server-generated brief even if it were correctly generated and stored |

---

## Failure Map

| Layer | Status | Root Cause |
|-------|--------|-----------|
| Server brief generation | Working (DailyBriefAgent) | — |
| Server brief storage | Working (writes to Supabase `daily_briefs`) | — |
| Scheduler trigger | Unreliable | Server restart resilience unknown |
| Legacy generator | Broken | Model attribute mismatch |
| Legacy sync service | Broken | Model attribute mismatch |
| Brief API endpoint | Missing | Not built |
| Android brief fetch | Missing | No endpoint to call |
| Android brief display | Wrong content | Displays local template |
| Push notification for brief | Missing | Not built |

---

## Brief Content Audit

### Current Brief Structure (DailyBriefAgent output)

Morning brief sections:
1. **Financial Snapshot** — month-to-date spend, income, net cashflow
2. **Pending Todos** — OPEN todos, prioritised by importance
3. **Recent FYIs** — informational events from last 24 hours
4. **Facts** — any new personal facts extracted
5. **Anomalies** — spend categories above 150% of prior month

Evening brief sections:
1. **Today's Activity** — signals processed, todos updated
2. **Financial Delta** — transactions since morning brief
3. **Tomorrow Preview** — todos due tomorrow

### What Is Missing from Brief Content

| Missing Element | Impact | Priority |
|-----------------|--------|---------|
| School events section | School-related todos mixed with general todos — no dedicated school view | HIGH |
| Voice captures | Voice-captured todos/notes not in brief | HIGH (V2 feature) |
| Spouse financial activity | Only one family member's data | MEDIUM |
| Upcoming recurring expenses | Monthly recurring costs not pre-shown | MEDIUM |
| Investment summary | SIP deductions shown as INVESTMENT — not summarised | MEDIUM |
| Salary confirmation | Whether current month salary has been received | HIGH |
| Weather / Calendar integration | External context for the day | LOW |

---

## Brief Quality Audit

### What Works When Brief Is Generated

When the `DailyBriefAgent` runs successfully:

- Todos are correctly retrieved by priority (CRITICAL, HIGH first)
- FYI events from last 24 hours are included
- Monthly financial snapshot (accounting spend, lifestyle spend, income, net cashflow) is correct — sourced from the pre-computed `monthly_spending_summary` table
- Anomalies are flagged when category spend exceeds 150% of prior month

### What Produces Low-Quality Brief Content

1. **Missing merchant-level breakdown** — brief says "₹8,450 on FOOD_DINING" but doesn't list Zomato vs. Swiggy split
2. **No school event prioritisation** — school circulars and parent meetings buried among general FYIs
3. **FYI flood** — multiple FYIs from the same delivery package inflate the FYI section
4. **Todo duplication** — same bill alert creates multiple todos across days, all appearing in brief

---

## What the User Actually Wants in a Daily Brief

Based on the original product vision and known failure patterns:

### Morning Brief (Ideal — Under 2 Minutes to Read)

```
Good morning, Pradeep. Here's your 5-second summary:

MONEY
  • You've spent ₹34,200 this month (₹18,400 lifestyle, ₹15,800 investments/bills)
  • Salary received: ₹95,000 on July 1
  • 3 new transactions yesterday: Zomato ₹450, BigBasket ₹1,200, Airtel ₹799

SCHOOL
  • Charan: Parent-teacher meeting on July 10 (9:00 AM) — confirm attendance
  • Chinicka: Sports day on July 15 (half day) — check if permission slip required

TODAY'S TASKS (3 due today)
  1. HDFC credit card bill due — ₹28,500 (today)
  2. Jio postpaid payment — ₹749 (today)
  3. Charan's library books return (2 days overdue)

ALERTS
  • Food spending this month is 35% higher than June (₹12,450 vs ₹9,200)
```

This is the target experience. The brief should be **scannable in under 30 seconds** and **actionable immediately**.

---

## Root Cause Analysis

The Daily Brief failure is not a single bug. It is a layered failure:

1. **Legacy code left in place** — `daily_brief_generator.py` and `supabase_sync_service.py` were deprecated but not removed, creating confusion about which generator is the authoritative one
2. **Model schema not reconciled** — the deprecated code references the old model schema which no longer matches the current model
3. **API layer never built** — the backend has no endpoint for the Android app to fetch briefs
4. **Android never updated** — the Android app was not updated to consume the server brief; it still assembles locally
5. **End-to-end testing not performed** — the brief generation works in isolation but the full path was never tested end-to-end

---

## Priority Fix List for V2

Listed in dependency order:

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| 1 | Remove `daily_brief_generator.py` and `supabase_sync_service.py` | Low | Eliminates confusion |
| 2 | Verify `DailyBriefAgent` generates and stores briefs correctly | Low | Confirms generation works |
| 3 | Build `GET /briefs/latest` API endpoint | Low | Enables Android delivery |
| 4 | Update `InsightSyncWorker` to call the brief API endpoint | Medium | Android receives the brief |
| 5 | Update `DailyBriefScreen.kt` to display the remote brief | Medium | User sees the real brief |
| 6 | Add push notification when brief is generated | Medium | User is alerted to check |
| 7 | Verify scheduler survives server restart | Low | Brief runs reliably |
| 8 | Add `run_consumer_sync` as a recurring scheduler job | Medium | Signals are always up to date |
| 9 | Add school section to brief content | Medium | Highest-value missing section |
| 10 | Add voice capture path to brief | High | V2 feature |

---

## What to Preserve

| Component | Preserve? | Reason |
|-----------|-----------|--------|
| `src/agents/daily_brief/agent.py` | Yes | Correct implementation, correct schema |
| `DailyBrief` SQLAlchemy model | Yes | Correct |
| `daily_briefs` Supabase table | Yes | Correct schema |
| `JarvisScheduler` (brief jobs) | Yes | Jobs registered correctly |
| Morning/Evening brief structure | Yes | Content structure is good |

## What to Discard

| Component | Discard? | Reason |
|-----------|---------|--------|
| `services/daily_brief_generator.py` | Yes | Deprecated; crashes on execution; model mismatch |
| `services/supabase_sync_service.py` | Yes | Deprecated; crashes on execution; model mismatch |
| Local brief assembly in `InsightSyncService.kt` | Yes | Conflicts with server-generated brief |

---

*Document: 07_DAILY_BRIEF_AUDIT.md*  
*Part of Jarvis V1 Migration Knowledge Base*
