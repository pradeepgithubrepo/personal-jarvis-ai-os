# Jarvis V1 — Executive Summary

> Migration Knowledge Base · Document 00  
> Produced: 2026-07-04 · Source: Full V1 codebase analysis

---

## 1. Original Jarvis Vision

Jarvis was conceived as a **personal AI operating system** for a single family unit. The core problem it solves is signal noise: a modern person receives hundreds of digital signals every day — bank alerts, insurance reminders, appointment confirmations, WhatsApp group messages, delivery updates, school circulars, salary credits, refunds. Most of this is noise. A small subset is genuinely actionable or worth knowing.

Without a system, the user manually filters everything. Every day. Forever.

The original vision:

- Know the user's complete financial picture in real time (income, spending, trends, anomalies)
- Maintain a personal fact database — employers, insurance policies, subscriptions, family appointments
- Generate a Daily Brief every morning — personalised, context-aware, accurate
- Never require the user to check raw SMS or email to know what happened financially
- Eventually process signals at the OS level on Android — a private, on-device AI layer that replaces manual app-checking

The system was deliberately designed for a **single user household** (Pradeep, spouse Shobana, children Charan and Chinicka). It is not a multi-tenant product.

---

## 2. Current State of V1

### What Is Running

The backend is a **Python FastAPI server** running on a home server. It processes:

1. **SMS signals** — intercepted by the Android app (`jarviscollector`) and uploaded to Supabase Storage as JSON files
2. **WhatsApp notifications** — captured at OS level by the Android notification listener
3. **Email** — polled from Gmail via OAuth

The pipeline runs on a scheduled cadence. The Android app syncs 3x daily (05:55, 13:55, 20:55) to precede backend pipeline execution.

### Backend Pipeline State

The pipeline is modular and largely functional:

| Module | Status |
|--------|--------|
| Consumer (signal ingestion) | Working |
| Signal Qualification Agent | Working |
| Signal Understanding Agent | Working (deterministic + LLM hybrid) |
| Financial Agent | Working |
| Aggregation Service | Working |
| Todo Agent | Working |
| FYI Agent | Working (facade wrapper around core agent) |
| Fact Agent | Working |
| Daily Brief Agent | Partially working — schema conflicts present |
| Scheduler | Heartbeat only — brief jobs registered but consumer sync not scheduled |

### Android App State

The Android app (`jarviscollector`) is functional as an ingestion client:
- SMS reading via `Telephony.Sms.Inbox.CONTENT_URI` — reliable
- WhatsApp notification capture via `NotificationListenerService` — reliable
- Upstream signal upload to Supabase Storage — working
- Downstream sync of Todos, Financial Events, FYIs — working
- Daily Brief display — **broken**: built from local template, not from server-generated brief

### Streamlit Dashboard State

A web-based dashboard (`streamlit_app_v2`) provides:
- Financial summaries (accounting spend vs. lifestyle spend)
- Monthly category trends
- Todo/FYI/Fact exploration
- Diagnostics and signal inspection

The dashboard is functional but used only by the owner for monitoring.

### Known Active Failures

1. `services/daily_brief_generator.py` — crashes on execution (missing model attributes `date`, `content_json`, `sync_status`)
2. `services/supabase_sync_service.py` — same model mismatch crashes
3. Android Daily Brief screen — displays locally assembled template, not LLM brief
4. No API endpoint for Android to retrieve generated briefs from Supabase
5. Scheduler does not schedule `run_consumer_sync` as a recurring job — only the `runtime_heartbeat` fires
6. Legacy `signal_processor.py` (28KB) still exists alongside the modular pipeline — dual-path ambiguity

---

## 3. Major Strengths

### 3.1 Financial Intelligence is Sophisticated

The financial processing layer is the most mature component:
- **4-condition internal transfer detection** — prevents false positive transfer identification
- **4-tier salary detection** — keyword → registry → pattern → large-credit fallback
- **Refund-as-offset semantics** — refunds reduce prior spending, never inflate income
- **Accounting Spend vs. Lifestyle Spend split** — a meaningful distinction that most consumer apps miss
- **Pre-seeded merchant registry** — 24 merchants, 45+ aliases, works from first run
- **Full signal lineage** — every fact traces back to the raw signal

### 3.2 Agent Architecture is Clean

The separation of responsibilities across agents (Qualification → SUA → Financial Agent → Aggregation → Todo/FYI/Fact → Daily Brief) is architecturally sound. Each agent has documented boundaries and exclusive ownership of its tables.

### 3.3 Deterministic-First Processing

The Signal Understanding Agent attempts a deterministic path before invoking the LLM. This means 60–80% of signals are processed with confidence = 1.0, zero latency, zero LLM cost.

### 3.4 Android Capture is Reliable

SMS and WhatsApp capture on the Android device work well. Signal deduplication via SHA-256 hashing prevents double-processing.

### 3.5 Signal Qualification is Effective

The qualification agent filters aggressively before any LLM is invoked. OTPs, promotional SMS, WhatsApp system noise, stale signals — all rejected before touching the expensive pipeline. The financial preservation override ensures no real transaction is silently dropped.

---

## 4. Major Weaknesses

### 4.1 Daily Brief is the Most Broken Component

The single most user-visible feature is unreliable. Two separate implementations exist with incompatible schemas. The Android app builds briefs locally from templates instead of consuming server-generated content. There is no API endpoint to deliver the brief to the Android app.

### 4.2 Voice Capture Does Not Exist

There is no voice capture capability anywhere in V1. Every capture mechanism requires typing or relies on automated SMS/notification interception. This is a critical gap for daily assistant usage.

### 4.3 GPay Lite Funding and Wallet Spending are Invisible

When money flows through a GPay or Paytm wallet, the underlying spend is invisible. The bank SMS shows a wallet top-up debit but the individual wallet transactions are never captured.

### 4.4 The Android Dashboard is Too Complex

The Android app has 11 screens. Many are nearly identical code. The complexity exceeds what users actually engage with.

### 4.5 Schema Drift Between SQLite and Supabase

Multiple tables have evolved inconsistently between the local SQLite schema and the remote Supabase schema. This causes runtime crashes.

### 4.6 The Legacy Pipeline is Not Decommissioned

`services/signal_processor.py` — the original monolithic pipeline — still exists alongside the new modular architecture, creating ambiguity.

### 4.7 Mutual Fund / SIP Classification is Incomplete

Many direct SIP debits via NACH from bank accounts are classified as `OTHER` because the NACH mandate descriptions are non-standard.

### 4.8 Spouse Adoption is Zero

Shobana has no Jarvis interface. A family AI assistant that only serves one family member is underutilising its potential.

### 4.9 Review Queue Has No UI

Signals scoring 21–59 are placed in REVIEW status with no way to inspect or act on them.

---

## 5. Key Lessons Learned

### L-1: Reliability is More Important Than Feature Count

The Daily Brief is the highest-value feature. It is broken. Users do not care about sophistication — they care about waking up and seeing a brief that is correct and fresh. A system with 2 working features that never break beats a system with 12 features where 3 are broken.

### L-2: Users Want Summaries, Not Dashboards

The Streamlit dashboard has financial charts, trend graphs, category breakdowns, merchant views, signal inspection, and diagnostics. The owner uses it occasionally for debugging. The spouse has never opened it. The value is in the Daily Brief.

### L-3: Voice Capture is Critical

Every time a thought arises ("I need to pay the water bill"), the user has to remember it until they are at a keyboard. Voice capture — saying something to Jarvis and having it captured immediately — is the missing killer feature.

### L-4: Financial Consumption Matters More Than Bank Debits

What the user wants to know is: "What did I actually spend money on this month?" Bank debits are a proxy for spending, not the thing itself. Wallet spend, card-behind-card spend, and UPI-to-wallet spend are all invisible.

### L-5: Freshness Drives Engagement

A Daily Brief from 3 days ago is useless. A Daily Brief from this morning is valuable. If the brief arrives stale or not at all, the user stops checking.

### L-6: Spouse Adoption is the Strongest Success Metric

The system is designed for a family. If only one family member uses it, it captures only half the picture. A system adopted by both spouses is twice as valuable.

### L-7: The Agent Architecture is Worth Keeping

The modular agent architecture is sound. The problem is not the architecture — it is that some modules are incomplete, some are broken, and the pipeline lacks operational reliability.

---

## 6. Recommended Direction for V2

### Core Principle: Reliability Over Features

V2 must start by defining the minimum lovable product and making it bulletproof.

The minimum lovable product:
1. **Voice capture** — user can say something and it is captured
2. **Todo management** — bills due, school events, medical reminders
3. **Daily Brief** — every morning, always, summarising what matters
4. **Financial insights** — spending this month, income, top categories
5. **School events** — with dates and reminders

Everything else is post-MVP.

### Architecture Recommendation

Keep the modular backend architecture. Fix the broken pieces. Simplify the Android UI to 4 screens: Home (brief), Todos, Finance, Capture. Deliver the brief via push notification. Add spouse support from day one. Define what financial data is visible vs. invisible and be honest about it.

### What to Discard

- The legacy `signal_processor.py` — decommission immediately
- The Streamlit dashboard as a primary interface — keep as debugging tool only
- The 5 nearly-identical category screens — fold into a single filtered view
- `daily_brief_generator.py` and `supabase_sync_service.py` — broken, replaced by DailyBriefAgent

### North Star for V2

> **Jarvis should feel like a capable family assistant who always shows up, never misses your bills, knows your spending, remembers your school schedules, and gives you a morning summary you actually read.**

---

*Document: 00_EXECUTIVE_SUMMARY.md*  
*Part of Jarvis V1 Migration Knowledge Base*
