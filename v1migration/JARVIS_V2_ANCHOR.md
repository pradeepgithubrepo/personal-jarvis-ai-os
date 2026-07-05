# Jarvis — V2 Migration Anchor Document

> The single source of truth for the V2 build effort.  
> Produced: 2026-07-04 · Generated from full V1 codebase analysis.

---

## Read This First

This document is the master anchor for anyone working on Jarvis V2. It does not replace the ten detailed documents in `v1migration/` — it references them and provides the minimum context needed to get oriented and take action.

**Before writing code:** Read `10_V2_BUILD_CONSTITUTION.md`  
**Before modifying the pipeline:** Read `03_BACKEND_STATE.md` and `05_PIPELINE_AUDIT.md`  
**Before touching financial logic:** Read `06_FINANCIAL_INTELLIGENCE_AUDIT.md`  
**Before touching the brief:** Read `07_DAILY_BRIEF_AUDIT.md`  
**Before touching Android:** Read `02_ANDROID_STATE.md`

---

## 1. What Jarvis Is

Jarvis is a personal AI operating system for a single family unit (Pradeep, spouse Shobana, children Charan and Chinicka). It processes SMS, WhatsApp, and email signals to produce a Daily Brief every morning, maintain a task list, track household finances, and store personal facts.

It is not a multi-tenant product. It is not a general-purpose assistant. It is designed for this specific family.

---

## 2. The North Star

> **Jarvis should feel like a capable family assistant who always shows up, never misses your bills, knows your spending, remembers your school schedules, and gives you a morning summary you actually read.**

Every V2 decision is evaluated against this standard.

---

## 3. Current System State (V1)

| Component | Status | Priority Fix |
|-----------|--------|-------------|
| Signal ingestion (Android → Supabase) | Working | — |
| Signal qualification | Working | — |
| Signal understanding (SUA) | Working | Remove shadow mode artifact |
| Financial Agent | Working | Deploy missing Supabase tables |
| Aggregation Service | Working | — |
| Todo Agent | Working | Add lifecycle management |
| FYI Agent | Working | — |
| Fact Agent | Working | — |
| **Daily Brief generation** | **Broken** | **Priority 1 — fix end-to-end** |
| Android brief delivery | Broken | Fix with brief API endpoint |
| Consumer sync scheduling | Broken | Add as recurring job |
| LLM mock in orchestrator | CRITICAL BUG | Remove `_instrumented_ask` immediately |

---

## 4. What Must Be Removed Before V2

Remove these components before starting any V2 build. They are deprecated, broken, or harmful.

| File | Remove Reason |
|------|--------------|
| `services/daily_brief_generator.py` | Deprecated; crashes on execution |
| `services/supabase_sync_service.py` | Deprecated; crashes on execution |
| `services/signal_processor.py` | Legacy monolithic pipeline; superseded |
| `services/financial_intelligence.py` | Not V2-aligned; superseded |
| `_instrumented_ask` in `pipeline_orchestrator.py` | Production mock; corrupts pipeline |
| `run_shadow_mode()` in `signal_understanding_agent.py` | Development artifact |
| Local brief assembly in Android `InsightSyncService.kt` | Conflicts with server brief |
| `FamilyScreen.kt`, `SchoolScreen.kt`, `TravelScreen.kt`, `HealthScreen.kt`, `ShoppingScreen.kt` | Duplicate code; consolidate |

---

## 5. V2 Feature Scope (8 Features)

Listed in priority order. **Do not start Feature N+1 until Feature N is validated.**

### Priority 1 — Daily Brief (End-to-End Fix)

The brief must be generated daily, stored in Supabase, delivered to Android via push notification, and display LLM-generated content (not local template).

**Key items:**
- Build `GET /briefs/latest` API endpoint
- Update `InsightSyncWorker` to fetch brief from API
- Update `DailyBriefScreen.kt` to display remote brief
- Fix scheduler `run_consumer_sync` (add as recurring job)
- Add brief generation retry logic

**Done when:** Morning brief arrives on Android every day for 30 days without manual intervention.

---

### Priority 2 — Operational Reliability

- Add `pipeline_runs` and `system_status` Supabase tables
- Deploy `transfer_pairs` and `salary_sources` Supabase migrations
- Remove mock from orchestrator
- Log all scheduled job runs

---

### Priority 3 — Voice Capture

Add a Capture screen to Android. Tap-to-speak. Transcription sent to `POST /capture/voice` API. Creates todo or fact via SUA. Appears in next brief.

**Done when:** User says "Pay electricity bill by Friday" → todo appears within 60 seconds.

---

### Priority 4 — Todo Lifecycle Fix

- Swipe-to-complete in TodoScreen
- Auto-close: payment SMS closes related bill-due todo
- Snooze (24-hour defer)
- Basic duplicate detection

---

### Priority 5 — School Events

- Tag school-related signals as `school_event` FYI sub-type
- School events appear as a dedicated section in the brief
- School fee reminders create todos with category `SCHOOL`

---

### Priority 6 — Android UI Simplification

- Collapse 11 screens to 4: Home, Todos, Finance, Capture
- FYI screen with category filter (replaces 5 category screens)

---

### Priority 7 — Spouse Onboarding

- Shobana installs app; signals tagged with device/user identity
- Signals processed into shared pipeline
- Brief includes spouse's school signals

---

### Priority 8 — Financial Brief Quality

- Brief shows: salary status, lifestyle spend, top 3 categories, investment total
- Label: "Based on bank SMS only"
- Bootstrap salary registry from historical data

---

## 6. Locked Constraints

These are permanent. They cannot be changed without product owner approval.

| Constraint | Rule |
|-----------|------|
| Qualification before LLM | No raw signal reaches LLM without qualification |
| Deterministic before LLM | Rule engine fires first; LLM handles residual |
| One owner per table | No table has two writers |
| FINANCIAL class boundary | FINANCIAL only if money has already moved |
| No mock in production | `tests/` only |
| Supabase is source of truth | SQLite is cache only |
| Refunds offset spending, never inflate income | Permanent |
| Internal transfers excluded from all spend | Permanent |
| No downstream agent parses raw messages | Contract is the only interface |

---

## 7. The Pipeline (Authoritative Sequence)

```
Android SMS / WhatsApp capture
    ↓
Supabase Storage (incoming/)
    ↓
ConsumerService — poll every 15 minutes
    ↓
mobile_signals (SQLite)
    ↓
SignalQualificationAgent
    ↓ (QUALIFIED only)
SignalUnderstandingAgent → canonical contract
    ↓
    ├── FINANCIAL → FinancialAgent → FinancialFact → AggregationService → rollup tables
    ├── ACTION → TodoAgent → todo_items
    ├── INFORMATION → FyiAgent → fyi_events
    └── MEMORY → FactAgent → facts
    ↓
DailyBriefAgent (06:00 and 20:00 cron)
    ↓
daily_briefs (Supabase)
    ↓
GET /briefs/latest (API endpoint)
    ↓
InsightSyncWorker (Android)
    ↓
DailyBriefScreen.kt
    ↓
Push notification → User
```

---

## 8. V2 Migration Document Index

| Doc | Title | Purpose |
|-----|-------|---------|
| [00](v1migration/00_EXECUTIVE_SUMMARY.md) | Executive Summary | Big picture — what V1 was, what V2 needs to be |
| [01](v1migration/01_PRODUCT_CAPABILITIES.md) | Product Capabilities Inventory | What exists, what works, what to keep or discard |
| [02](v1migration/02_ANDROID_STATE.md) | Android State | Full Android app component audit |
| [03](v1migration/03_BACKEND_STATE.md) | Backend State | All backend services — status, keep/discard/refactor |
| [04](v1migration/04_SUPABASE_SCHEMA_AUDIT.md) | Supabase Schema Audit | All tables — owners, status, missing tables |
| [05](v1migration/05_PIPELINE_AUDIT.md) | Pipeline Audit | All pipelines, schedules, failure points |
| [06](v1migration/06_FINANCIAL_INTELLIGENCE_AUDIT.md) | Financial Intelligence Audit | Financial algorithms, gaps, what users need |
| [07](v1migration/07_DAILY_BRIEF_AUDIT.md) | Daily Brief Audit | Why the brief is broken and how to fix it |
| [08](v1migration/08_LESSONS_LEARNED.md) | Lessons Learned | Every lesson from V1, with V2 implications |
| [09](v1migration/09_V2_MINIMUM_VIABLE_SCOPE.md) | V2 Minimum Viable Scope | What must be built, in what order |
| [10](v1migration/10_V2_BUILD_CONSTITUTION.md) | V2 Build Constitution | Permanent constraints and governing principles |

---

## 9. Validation Requirement (Non-Negotiable)

Every V2 feature requires:
1. Shadow validation against real production signals before going live
2. A written validation report (what was tested, what passed, what failed, alignment %)
3. A `pipeline_runs` record for every automated execution after deployment

**A feature without a validation report is not complete.**

---

## 10. One-Sentence Summary

Jarvis V2 fixes the Daily Brief end-to-end, adds voice capture, cleans up 4 years of accumulated technical debt, and adds spouse support — without changing the core agent architecture, which is sound.

---

*Document: JARVIS_V2_ANCHOR.md*  
*Jarvis V1 Migration Knowledge Base — Master Anchor*  
*Produced: 2026-07-04*
