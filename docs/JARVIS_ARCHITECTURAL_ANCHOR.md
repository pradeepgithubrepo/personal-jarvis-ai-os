# JARVIS AI OS — Architectural Anchor Document

> **Canonical Source of Truth — Do Not Summarise, Do Not Contradict**
> Version: 1.0 · Produced: 2026-06-25 · Author: Engineering + AI Pair
> Repository: `/home/prad/petprojects/ai/jarvis`

---

## PREFACE

This document is the permanent engineering handoff for the Jarvis AI OS project.

It was written at the boundary of a context window, after months of design, implementation, validation, and iteration. Every section is based on real production code, real architectural decisions, and real lessons learned — not aspirations or plans.

If you are an LLM reading this: **do not redesign anything documented in this file without explicit instruction from the product owner.** Every decision here was made deliberately, tested against real data, and locked for good reason.

---

## 1. Executive Overview

### What Jarvis AI OS Is

Jarvis is a personal AI operating system for a single user. It runs on the user's own hardware (a home server), processes signals from the user's daily digital life — SMS messages, WhatsApp, email — and transforms them into structured, actionable intelligence.

The system does not make decisions for the user. It surfaces facts, priorities, and trends, and presents them in a Daily Brief. The user remains in control. Jarvis provides context.

### Why It Exists

The problem Jarvis solves is **signal noise**. A modern person receives hundreds of digital signals every day. Bank alerts, insurance reminders, appointment confirmations, family messages, delivery updates, salary credits, refunds. Most of these signals are noise. A small subset are genuinely actionable or worth remembering.

Without a system, the user manually filters all of this. Every day. Forever.

Jarvis automates the filter. It qualifies signals, understands them, classifies them, extracts financial facts, creates todos, files information, and builds a financial picture — so the user receives a daily brief that contains only what matters.

### Long-Term Vision

Jarvis evolves toward a system that:

1. Knows the user's complete financial picture in real time (income, spending, trends, anomalies)
2. Maintains a personal fact database — the user's employers, insurance policies, subscriptions, family health appointments
3. Generates a Daily Brief every morning — personalised, context-aware, accurate
4. Never requires the user to look at raw SMS or email to know what happened financially
5. Eventually integrates with the Android device directly, processing signals at the OS level

The long-term goal is a **private, on-device AI layer** that replaces the need for the user to check multiple apps, manually categorise bank statements, or remember deadlines.

### Agent-First Philosophy

Every processing function in Jarvis is owned by a named agent with a documented purpose and strict boundaries. Agents do not share responsibilities. If a function belongs to the Financial Agent, no other agent touches it. If a function belongs to the Qualification Agent, no other agent overrides it.

This makes the system:
- Debuggable: when something is wrong, exactly one agent is responsible
- Testable: each agent can be validated in isolation
- Evolvable: an agent can be upgraded without affecting others

### Quality-First Philosophy

Jarvis does not ship features fast. It ships features correctly. This means:
- Every new agent must be validated against real production data before going live
- Shadow mode is used to run new logic in parallel with the existing system before replacing it
- Validation reports document what was tested, what passed, and what failed
- Known limitations are documented, not hidden

A pipeline that produces wrong data is worse than no pipeline. Wrong financial categorisation misleads the user. Wrong qualification lets noise through. Wrong salary detection corrupts the monthly brief.

Quality is not a phase. It is the permanent operating mode.

### Why Deterministic Processing Always Precedes LLM Reasoning

LLMs are probabilistic. They can misread a message. They can assign a wrong class. They are expensive (latency and compute). They are not reproducible — the same message can produce a different result on different days.

Deterministic rules are none of these things. A regex match is correct every time. A keyword list is verifiable. A rule can be unit-tested.

The principle is: **do everything possible with rules before asking the LLM**. The LLM processes only the signals that the rules cannot handle. On a typical day, the rules handle 60–80% of all signals. The LLM handles the rest.

This also means that when a rule fires, the output is `confidence = 1.0`. This is not an approximation. The rule matched exactly. This is a different epistemic category from LLM output.

### Why Modularity Is More Important Than Rapid Implementation

A monolithic pipeline was the first implementation of Jarvis. It worked, but it mixed qualification, classification, financial extraction, and aggregation in a single function. When a bug appeared, it was impossible to know which stage introduced it. When a new signal type was added, it required changes across multiple interlocked functions. When the output was wrong, re-running required re-running everything.

The modular architecture that replaced it has a higher upfront cost. Each module requires documented boundaries, integration points, and validation. But it produces a system where:
- Each module can be tested independently
- Failures are isolated to one module
- A new module can be added without modifying existing ones
- The pipeline can be replayed from any stage

Speed was sacrificed for correctness. This was the right trade.

---

## 2. Architectural Evolution

### Phase 0 — Original Monolithic Pipeline

**What existed:** A single Python script, `signal_processor.py`, that read raw SMS/WhatsApp/email messages and attempted to do everything: filter noise, classify the message, extract financial details, store the result.

**What it produced:** Financial event records in SQLite. Spending summaries. A rudimentary daily brief.

**Why it worked at first:** Small volume, single developer, no performance requirements, no quality requirements. Every message was processed. Most were wrong.

**Problems discovered:**
- Financial transactions from bank SMS were correctly detected, but so were promotional SMS, OTP messages, and telecom alerts — all classified as financial events
- No de-duplication: the same SMS processed twice created two financial events
- No age filtering: stale historical SMS from years ago were processed as current
- No confidence model: every result was treated as equally reliable
- No separation between "money moved" (FINANCIAL) and "money might move" (bill due alerts, insurance renewal reminders) — both were incorrectly routed to financial processing
- Internal transfers (moving money between user's own accounts) were counted as spending
- Refunds were counted as income, inflating the income figures
- Aggregation was embedded in the same class as classification — one bug affected both

### Phase 1 — Qualification Agent (Module 2A)

**What changed:** Introduced `SignalQualificationAgent` as the first layer of the pipeline. All raw signals pass through qualification before any downstream processing.

**Why the pivot happened:** The monolithic pipeline was processing everything. The financial summaries were meaningless because promotional SMS, OTPs, and system notifications were included. The first fix was to stop processing noise before doing anything else.

**What qualification introduced:**
- Age filter: SMS/email older than 90 days rejected immediately
- Duplicate detection: exact message match + amount match within 48-hour window
- OTP rejection: all OTP messages rejected (score 10)
- WhatsApp system noise rejection: call logs, media messages, system notifications
- Telecom noise rejection: data limit alerts, recharge notifications
- Promotional rejection: pre-approved loan offers, discount codes
- Financial advisory rejection: RBI safety tips, KYC update messages
- Family context boost: messages mentioning family members get +30 score
- High-value domain boost: messages in medical, financial, travel, legal domains get +30 score
- Financial preservation: messages with financial keywords are never silently rejected — they go to REVIEW instead

**Result:** The noise floor dropped dramatically. Only genuinely interesting signals proceeded downstream.

### Phase 2 — Signal Understanding Agent (Module 3)

**What changed:** Introduced `SignalUnderstandingAgent` to replace the ad-hoc classification in the monolithic pipeline.

**Why the pivot happened:** After qualification, the remaining signals still needed to be understood. The old classification was a flat keyword scan that produced categories but not structured knowledge. It could not extract amounts, merchants, deadlines, or importance. It could not distinguish between "money moved" and "money might move."

The SUA produces a **canonical signal contract** — a structured JSON document that is the single output format all downstream agents consume. Downstream agents never parse raw messages. They read the contract.

**What the SUA introduced:**
- Deterministic path: regex + keyword rules that handle the majority of known signal types with `confidence = 1.0`
- LLM path: a structured prompt for signals the deterministic path cannot handle
- Business confidence model: a hybrid score that accounts for source reliability, entity completeness, and parse quality
- Canonical classes: FINANCIAL, INFORMATION, ACTION, ALERT, MEMORY
- Routing: the contract specifies which downstream agents receive it (`routes` field)
- Shadow mode: run in parallel with old pipeline to validate before going live

**Critical semantic boundary established here:** A signal is FINANCIAL only if money has already moved. Future obligations (bill due alerts, insurance renewal reminders) are INFORMATION + ACTION, not FINANCIAL. This boundary prevents the Financial Agent from recording events that have not happened.

### Phase 3 — Financial Agent (Module 4)

**What changed:** Introduced `FinancialAgent` as the dedicated processor of FINANCIAL class contracts.

**Why the pivot happened:** The monolithic pipeline's financial processing had accumulated six known defects:
1. Internal transfer detection used only amount match — false positives on coincidental same-amount transactions
2. Salary detection relied only on the keyword "salary" — missed employer NEFT credits without that label
3. Spending views were a single total — SIP investments and insurance premiums were indistinguishable from lifestyle spending
4. Refund treatment was undefined — refunds were counted as income
5. Merchant registry was empty on first run — 100% unclassified until transactions accumulated
6. Aggregation and fact writing were mixed in the same class — impossible to re-run aggregation without re-running classification

The Financial Agent replaced all of this with a structured, typed fact model with full signal lineage.

**What the Financial Agent introduced:**
- `FinancialFact` — a typed ledger record for every monetary event
- 4-condition internal transfer detection (see Section 9)
- 4-tier salary detection algorithm (see Section 9)
- Refund-as-offset semantics: refunds reduce prior spending, never inflate income
- Pre-seeded merchant registry: 24 canonical merchants with 45+ aliases, active from first run
- Two spending views: Accounting Spend and Lifestyle Spend
- Full signal lineage: fact → financial_event → understood_signal → qualified_signal → raw_signal

### Phase 4 — Aggregation Service (Module 4B)

**What changed:** Extracted rollup computation from `FinancialAggregator` into a separate `AggregationService` class.

**Why the pivot happened:** The Financial Agent's job is to produce facts. Aggregation — computing monthly totals, category breakdowns, MoM trends — is a separate concern. Mixing them in one class meant:
- A bug in aggregation logic could corrupt fact records
- Re-running aggregation required re-running classification (expensive)
- Aggregation is idempotent; fact writing is not — they have different reliability guarantees

**Result:** `AggregationService` reads facts (read-only) and writes rollup tables. It is safe to re-run any number of times. The fact tables are never touched.

---

## 3. Locked Architecture

### 3.1 Consumer

**Purpose:** Ingests raw signals from all sources (SMS via Android app, WhatsApp via parser, email via IMAP) and stores them as raw `MobileSignal` records in SQLite.

**Inputs:** Android ADB bridge / IMAP / WhatsApp export files

**Outputs:** Raw `mobile_signals` records in SQLite (unprocessed flag = True)

**Database ownership:** Writes to `mobile_signals` (SQLite). Writes to `signals` (Supabase) via sync.

**Must do:**
- Store every signal exactly once (idempotent — check for existing record before inserting)
- Preserve the original timestamp from the source
- Set `processed = False` on all new records (marks them as waiting for Qualification)
- Record source metadata (SMS sender, WhatsApp group name, email sender)

**Must NEVER do:**
- Filter signals (qualification does this)
- Classify signals (SUA does this)
- Modify signal content
- Route to downstream agents
- Touch the `qualified_signals` table

---

### 3.2 Scheduler / Pipeline Orchestrator

**Purpose:** Runs the pipeline on a schedule and sequences all agents in the correct order. Prevents concurrent pipeline runs. Tracks run history.

**File:** `services/pipeline_orchestrator.py`

**Inputs:** Timer trigger (cron or manual invocation)

**Outputs:** `pipeline_runs` record in SQLite + Supabase with run stats

**Database ownership:** Writes to `pipeline_runs`, `system_status` (both SQLite + Supabase)

**Must do:**
- Acquire a run lock before starting (check `system_status.current_status == "RUNNING"` in Supabase)
- Release the lock on completion or failure
- Detect stale locks (set more than 30 minutes ago) and override
- Run agents in strict order: Consumer → Qualification → SUA → FinancialAgent → Aggregation → (future: Todo, FYI, Fact, DailyBrief)
- Track LLM call count for monitoring
- Record final stats: signals processed, todos generated, financial events generated, LLM calls, duration

**Must NEVER do:**
- Run two pipeline instances simultaneously
- Proceed if the lock acquisition fails
- Skip agents in the sequence
- Modify signal content

---

### 3.3 Qualification Agent

**Purpose:** Filters all raw signals into QUALIFIED, REVIEW, or REJECTED before any LLM is invoked.

**File:** `services/signal_qualification_agent.py`

**Inputs:** Unprocessed `MobileSignal` records from SQLite

**Outputs:** `QualifiedSignal` records in SQLite + Supabase

**Database ownership:** Writes to `qualified_signals` (SQLite + Supabase)

**Must do:**
- Process every unprocessed signal exactly once
- Apply all rejection filters in order (age, duplicate, OTP, noise, promo, advisory)
- Apply business context boosts (family context +30, high-value domain +30)
- Apply financial preservation override (never silently reject a financial signal)
- Assign a qualification score (0–90) and a status (QUALIFIED/REVIEW/REJECTED)
- Record reason code for every REJECTED or REVIEW signal

**Must NEVER do:**
- Parse the meaning of a message (SUA does this)
- Extract amounts or merchants (SUA does this)
- Route to downstream agents (SUA does this)
- Touch the `understood_signals`, `financial_events`, or `financial_facts` tables
- Apply LLM reasoning

---

### 3.4 Signal Understanding Agent

**Purpose:** Transforms qualified signals into the canonical signal contract. The contract is the only interface between the understanding layer and all downstream agents.

**File:** `services/signal_understanding_agent.py`

**Inputs:** `QualifiedSignal` records with `qualification_status == "QUALIFIED"`

**Outputs:** `UnderstoodSignal` records in SQLite + Supabase; canonical contract dict passed to downstream agents

**Database ownership:** Writes to `understood_signals` (SQLite + Supabase)

**Must do:**
- Attempt deterministic path first (regex + keyword rules)
- Fall back to LLM path only if deterministic returns None
- Calculate business confidence score for every contract
- Apply defensive corrections to LLM output (missing fields get safe defaults)
- Derive routing from classes (FINANCIAL → FinancialAgent, ACTION → TodoAgent, INFORMATION → FyiAgent, MEMORY → FactAgent)
- Store both the contract and the `is_verified` flag (true if confidence ≥ 0.85)

**Must NEVER do:**
- Compute financial totals, monthly summaries, or spending views
- Classify expense categories
- Detect internal transfers
- Detect salary events
- Write to `financial_events`, `financial_facts`, `qualified_signals`, or any rollup tables
- Pass a raw message string to downstream agents instead of a contract

---

### 3.5 Financial Agent

**Purpose:** Transforms FINANCIAL class contracts into typed `FinancialFact` records. The single authoritative source of all financial knowledge.

**File:** `services/financial_agent.py`

**Inputs:** Canonical signal contracts with `"FINANCIAL" in classes`

**Outputs:** `FinancialFact` records in SQLite; `financial_events` updates in SQLite + Supabase

**Database ownership:** Writes to `financial_events`, `financial_facts`, `bank_accounts`, `transfer_pairs`, `salary_sources`, `salary_events`, `merchants`, `merchant_profiles` (all SQLite)

**Must do:**
- Reject contracts without FINANCIAL class silently (return None)
- Persist idempotent `financial_event` (check by source_signal_id before creating)
- Run 4-condition internal transfer detection
- Run 4-tier salary detection
- Classify expense category using: merchant registry → seed list → rules engine → LLM fallback
- Set `is_excluded_from_accounting_spend = True` for INTERNAL_TRANSFER facts
- Set `is_excluded_from_lifestyle_spend = True` for INVESTMENT, INSURANCE_PAYMENT, BILL_PAYMENT_CC
- Preserve full signal lineage (fact references event, event references understood_signal, etc.)
- Process REFUND_EVENT facts by linking to originating expense and flagging it as refunded

**Must NEVER do:**
- Reclassify the signal type set by SUA (the contract is authoritative)
- Write to `qualified_signals` or `understood_signals`
- Compute monthly rollups or trends (AggregationService does this)
- Count a refund as income
- Count an internal transfer leg as spending

---

### 3.6 Aggregation Service

**Purpose:** Computes monthly rollup tables from `FinancialFact` records. Idempotent. Read-only access to facts.

**File:** `services/financial_aggregator.py` (class `AggregationService`) and `services/aggregation_service.py`

**Inputs:** `FinancialFact` records from SQLite (read-only)

**Outputs:** `monthly_spending_summary`, `monthly_category_spend`, `monthly_category_trends` in Supabase

**Database ownership:** Writes to `monthly_spending_summary`, `monthly_category_spend`, `monthly_category_trends` (Supabase). Reads from `financial_facts` but does NOT write to them.

**Must do:**
- Compute Accounting Spend per month (all debits excluding internal transfers)
- Compute Lifestyle Spend per month (Accounting Spend minus investments, insurance, CC payments)
- Compute total income per month (confirmed salary + other income)
- Compute net cashflow (income − accounting_spend)
- Apply refund offsets to category spend totals
- Compute MoM percentage changes per category
- Be safe to re-run any number of times on the same data (idempotent)

**Must NEVER do:**
- Write to `financial_facts` or `financial_events`
- Reclassify any event
- Count refunds as income
- Count internal transfers as spending
- Run in the same transaction as Financial Agent fact writes (separate service boundary)

---

### 3.7 Future — Todo Agent (Module 5A)

**Purpose:** Creates actionable todo items from ACTION class contracts.

**Inputs:** Canonical contracts with `"ACTION" in classes`

**Outputs:** `todos` table in Supabase

**Database ownership:** Writes to `todos` only

**Must do:**
- Extract due date / deadline from contract entities
- Set priority based on importance (CRITICAL → P0, HIGH → P1, etc.)
- Check for duplicate todos before creating (same signal should not create two todos)
- Link todo to source signal via `source_signal_id`

**Must NEVER do:**
- Parse the raw signal message
- Write to any financial table
- Override the Qualification Agent's rejection decisions

---

### 3.8 Future — FYI Agent (Module 5B)

**Purpose:** Records informational events for user awareness. No action required.

**Inputs:** Canonical contracts with `"INFORMATION" in classes`

**Outputs:** `fyi_events` table in Supabase

**Database ownership:** Writes to `fyi_events` only

**Must NEVER do:**
- Create todos
- Write to financial tables
- Parse raw signal messages

---

### 3.9 Future — Fact Agent (Module 5C)

**Purpose:** Extracts and stores long-lived personal facts from MEMORY class signals. Examples: employer name, insurance policy number, doctor name, school name.

**Inputs:** Canonical contracts with `"MEMORY" in classes`

**Outputs:** `facts` table in Supabase

**Database ownership:** Writes to `facts` only

**Design note:** Facts are entity-attribute pairs with source signal lineage. A fact can be updated (same entity, new attribute value) but not deleted. The fact history is preserved.

---

### 3.10 Future — Daily Brief Agent (Module 6)

**Purpose:** Synthesises all processed data from the current day into a structured brief for the user.

**Inputs:** Reads from `todos`, `fyi_events`, `facts`, `monthly_spending_summary`, `financial_facts` (read-only across all tables)

**Outputs:** `daily_briefs` table in Supabase; notification to user

**Database ownership:** Writes to `daily_briefs` only

**Must do:**
- Pull data from rollup tables (never re-compute what AggregationService already computed)
- Summarise pending todos by priority
- Include financial snapshot (income, spend, lifestyle spend, net cashflow)
- Highlight anomalies (category spend > 150% of prior month)
- Use LLM only for final prose generation (all data is pre-computed)

**Must NEVER do:**
- Re-classify any signal
- Re-compute financial totals (read from rollup tables only)
- Parse raw signal messages

---

## 4. Canonical Pipeline

```
[SOURCE: Android SMS / WhatsApp / Email]
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  CONSUMER                                               │
│  Reads raw signals from source                          │
│  Stores to: mobile_signals (SQLite)                     │
│  Syncs to:  signals (Supabase)                          │
└────────────────────────────┬────────────────────────────┘
                             │  Raw MobileSignal records
                             ▼
┌─────────────────────────────────────────────────────────┐
│  QUALIFICATION AGENT (Module 2A)                        │
│  Applies: age filter, duplicate check, noise filters,   │
│  OTP rejection, promo rejection, advisory rejection,    │
│  family context boost, high-value domain boost,         │
│  financial preservation override                        │
│  Output: QUALIFIED / REVIEW / REJECTED + reason code   │
│  Stores to: qualified_signals (SQLite + Supabase)      │
└────────────────────────────┬────────────────────────────┘
                             │  QUALIFIED signals only
                             ▼
┌─────────────────────────────────────────────────────────┐
│  SIGNAL UNDERSTANDING AGENT (Module 3)                  │
│  Path 1 — Deterministic (regex + keyword rules)        │
│           confidence = 1.0, no LLM invoked             │
│  Path 2 — LLM (Qwen3 or equivalent local model)        │
│           confidence = business confidence score        │
│  Produces: canonical signal contract (JSON)             │
│  Stores to: understood_signals (SQLite + Supabase)     │
└────────────────────────────┬────────────────────────────┘
                             │  Canonical contracts
                             │  (routed by contract.routes field)
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     [FINANCIAL]         [ACTION]      [INFORMATION]
         │                  │              │
         ▼                  ▼              ▼
┌──────────────┐   ┌──────────────┐  ┌──────────────┐
│ FINANCIAL    │   │ TODO AGENT   │  │ FYI AGENT    │
│ AGENT (M4)   │   │ (Module 5A)  │  │ (Module 5B)  │
│              │   │ (future)     │  │ (future)     │
│ • Transfer   │   │              │  │              │
│   detection  │   │ Creates      │  │ Records      │
│ • Salary     │   │ actionable   │  │ awareness    │
│   detection  │   │ todo items   │  │ events       │
│ • Refund     │   └──────────────┘  └──────────────┘
│   offsets    │
│ • Category   │
│   classify   │
│ • FinancialFact│
└──────┬───────┘
       │  FinancialFact records
       ▼
┌─────────────────────────────────────────────────────────┐
│  AGGREGATION SERVICE (Module 4B)                        │
│  Reads: financial_facts (read-only)                     │
│  Computes: accounting_spend, lifestyle_spend, income,   │
│            net_cashflow, category totals, MoM trends    │
│  Writes: monthly_spending_summary (Supabase)            │
│          monthly_category_spend (Supabase)              │
│          monthly_category_trends (Supabase)             │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
              [MEMORY class → FACT AGENT (future)]
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  DAILY BRIEF AGENT (Module 6 — future)                  │
│  Reads: rollup tables, todos, fyi_events, facts         │
│  Produces: structured daily brief                       │
│  Notifies: user (push notification / UI)                │
└─────────────────────────────────────────────────────────┘
```

### Hand-off Details

**Consumer → Qualification:** The Consumer sets `processed = False` on every new `MobileSignal`. The Qualification Agent queries for `processed == False`, processes each one, and marks them processed regardless of outcome.

**Qualification → SUA:** Only QUALIFIED signals proceed. The SUA queries `QualifiedSignal` records with `qualification_status == "QUALIFIED"` and cross-references `understood_signals` to skip already-processed ones.

**SUA → Downstream Agents:** The SUA produces a canonical contract dict. The `routes` field specifies which agents receive it. The pipeline orchestrator reads `routes` and dispatches accordingly.

**Financial Agent → Aggregation Service:** The Financial Agent calls `AggregationService.run()` after writing facts. The Aggregation Service reads from the fact tables and writes rollups. This is a same-process call but crosses a clear ownership boundary — the two never write to each other's tables.

---

## 5. Database Ownership Matrix

The cardinal rule: **exactly one service writes to each table**. Multiple readers are acceptable. Multiple writers are forbidden.

### SQLite (Runtime Cache — Local)

| Table | Owner (Writer) | Read By | Notes |
|---|---|---|---|
| `mobile_signals` | Consumer | Qualification Agent | Raw ingested signals |
| `qualified_signals` | Qualification Agent | SUA, Pipeline Orchestrator | Post-filter signals |
| `understood_signals` | Signal Understanding Agent | Financial Agent, Todo Agent, FYI Agent | Canonical contracts |
| `financial_events` | Financial Agent | Aggregation Service, Daily Brief Agent | Raw financial event per signal |
| `financial_facts` | Financial Agent | Aggregation Service, Daily Brief Agent | Typed fact ledger |
| `bank_accounts` | Financial Agent | Financial Agent (read for transfer detection) | Known user accounts |
| `transfer_pairs` | Financial Agent | Aggregation Service | Matched internal transfer pairs |
| `salary_sources` | Financial Agent | Financial Agent (Tier 2 salary detection) | Known employer registry |
| `salary_events` | Financial Agent | Aggregation Service, Daily Brief Agent | Detected salary credits |
| `merchants` | Financial Agent | Financial Agent, FinancialClassifier | Canonical merchant registry |
| `merchant_profiles` | Financial Agent | Daily Brief Agent | Per-merchant spend history |
| `pipeline_runs` | Pipeline Orchestrator | Monitoring | Run history |
| `system_status` | Pipeline Orchestrator | Pipeline Orchestrator (lock check) | Single row, run lock |
| `classification_cache` | FinancialClassifier | FinancialClassifier | LLM result cache |

### Supabase (Source of Truth — Remote)

| Table | Owner (Writer) | Read By | Notes |
|---|---|---|---|
| `signals` | Consumer (via SupabaseRepo) | Query API | Synced from SQLite |
| `qualified_signals` | Qualification Agent (via SupabaseRepo) | SUA, Query API | Synced from SQLite |
| `understood_signals` | SUA (via SupabaseRepo) | Financial Agent, Query API | Canonical contracts |
| `financial_events` | Financial Agent (via SupabaseRepo) | Aggregation Service, Query API | Financial events |
| `financial_transaction_classification` | Financial Agent | Query API | Classification records |
| `monthly_spending_summary` | Aggregation Service | Daily Brief Agent, Query API, UI | V2: accounting + lifestyle split |
| `monthly_category_spend` | Aggregation Service | Daily Brief Agent, Query API | Per-category monthly totals |
| `monthly_category_trends` | Aggregation Service | Query API, UI | MoM trend data |
| `transfer_pairs` | Financial Agent (via SupabaseRepo) | Aggregation Service | Transfer pair records |
| `salary_source` | Financial Agent | Financial Agent (Tier 2) | Employer registry |
| `salary_cycles` | Financial Agent | Daily Brief Agent | Salary cycle records |
| `todos` | Todo Agent | Daily Brief Agent, UI | Actionable items |
| `fyi_events` | FYI Agent | Daily Brief Agent, UI | Informational events |
| `facts` | Fact Agent | Daily Brief Agent, UI | Long-lived personal facts |
| `daily_briefs` | Daily Brief Agent | UI | Compiled daily brief |
| `system_status` | Pipeline Orchestrator | Pipeline Orchestrator | Lock record |
| `pipeline_runs` | Pipeline Orchestrator | Monitoring | Run history |

---

## 6. Canonical Signal Contract

The canonical signal contract is the JSON document produced by the Signal Understanding Agent and consumed by all downstream agents. It is the single interface between understanding and action. **No downstream agent is permitted to parse the raw signal message.** The contract is the truth.

### Complete Contract Schema

```json
{
  "signal_id": "uuid-string",
  "signal_type": "financial_transaction | general | insurance_renewal | medical_appointment | ...",
  "classes": ["FINANCIAL", "INFORMATION", "ACTION", "ALERT", "MEMORY"],
  "domains": ["FINANCE", "INSURANCE", "MEDICAL", "TRAVEL", "GENERAL"],
  "importance": "LOW | MEDIUM | HIGH | CRITICAL",
  "summary": "Human-readable one-line description of the signal",
  "confidence": 0.95,
  "reason": "Why this classification was assigned",
  "entities": {
    "people": ["name1", "name2"],
    "organizations": ["Sender Bank", "Merchant Corp"],
    "merchants": ["Zomato"],
    "monetary_value": {
      "amount": 450.00,
      "currency": "INR"
    },
    "deadlines": ["2026-07-01"],
    "appointments": [],
    "locations": [],
    "travel_bookings": {},
    "bills": {},
    "insurance_policies": {
      "insurer": "LIC of India"
    },
    "medical_events": {}
  },
  "routes": ["FinancialAgent", "FyiAgent"],
  "raw_context": {
    "source": "sms | whatsapp | email",
    "sender": "HDFCBK",
    "timestamp": "2026-06-25T00:00:00",
    "processing_path": "RULE_ENGINE | LLM",
    "llm_model_used": "none | qwen3:1.7b"
  }
}
```

### Field Explanations

**`signal_id`**: UUID inherited from the `QualifiedSignal`. Links this contract back through the full lineage chain.

**`signal_type`**: A descriptive string for human consumption and logging. Not used for routing. Routing is driven exclusively by `classes` and `routes`.

**`classes`**: The canonical classification array. These are the machine-readable flags that drive routing and downstream processing. Never add a class that is not in the approved set.

| Class | Meaning |
|---|---|
| `FINANCIAL` | Money has moved. A real debit or credit occurred. Send to Financial Agent. |
| `INFORMATION` | Something happened worth knowing. No action required. Send to FYI Agent. |
| `ACTION` | The user needs to do something. Create a Todo. Send to Todo Agent. |
| `ALERT` | High-priority awareness required. Combined with INFORMATION. |
| `MEMORY` | A long-lived fact about the user's world. Send to Fact Agent. |

**Critical boundary — FINANCIAL class:**
A signal receives the FINANCIAL class ONLY if money has already moved. Future obligations — a bill due alert, an insurance renewal reminder, a "your EMI will be deducted" notice — are NOT FINANCIAL. They are ACTION or INFORMATION. This is the most important semantic rule in the entire system.

**`domains`**: The subject domain of the signal. Used for context enrichment and future filtering. Current valid values: FINANCE, INSURANCE, MEDICAL, TRAVEL, LEGAL, GENERAL.

**`importance`**: The urgency level. Used by Todo Agent for priority and by Daily Brief for ordering.

| Value | Meaning |
|---|---|
| `LOW` | Routine, no special attention needed |
| `MEDIUM` | Worth noting, include in brief |
| `HIGH` | Important, surface prominently |
| `CRITICAL` | Immediate attention required (unauthorized transaction, medical emergency) |

**`summary`**: One sentence. Written for the user, not the machine. Used in the Daily Brief and FYI Agent.

**`confidence`**: Business confidence score (0.0–1.0). Not raw LLM confidence. See Section 8 for the calculation.

| Range | Meaning |
|---|---|
| ≥ 0.85 | Auto-process, no review needed |
| 0.50–0.84 | Route to agent but flag `requires_review = true` |
| < 0.50 | Critical Inbox — hold for user review before routing |

**`reason`**: The explanation for the classification. For RULE_ENGINE path: the specific rule that fired. For LLM path: the model's stated reason. Used for debugging and audit.

**`entities`**: Structured facts extracted from the signal. Downstream agents consume entities — they never re-parse the message to find the amount, merchant, or deadline.

**`routes`**: The list of agent identifiers that should receive this contract. Derived deterministically from `classes` in both the deterministic path and the LLM path. The LLM route mapping code applies the same mapping: FINANCIAL → FinancialAgent, ACTION → TodoAgent, INFORMATION → FyiAgent, MEMORY → FactAgent.

**`raw_context`**: Source metadata. The `processing_path` field tells downstream agents whether this contract came from a deterministic rule (always trust) or from the LLM (check confidence threshold). The `sender` field is used by the Financial Agent's confidence model to apply trusted sender boosts.

### Why Downstream Agents Must Never Parse Raw Messages

1. **The raw message is gone.** By the time a downstream agent runs, the original MobileSignal may have been archived or is inaccessible.
2. **Parsing is the SUA's job.** If two agents parse the same message independently, they may produce different results. The contract ensures a single authoritative interpretation.
3. **The raw message format varies.** HDFC SMS format is different from SBI SMS format, which is different from Airtel SMS format. The SUA handles this complexity once. Downstream agents should not need to know about SMS format variations.
4. **The contract is typed.** Amount is a `float`. Date is an ISO string. Merchant is a resolved string. The raw message is untyped text. Typed data is safer and simpler to consume.

---

## 7. Qualification Agent — Complete Specification

### Purpose

The Qualification Agent is the first line of defense against noise. It determines whether a raw signal is worth processing by any downstream agent. Every signal that reaches the LLM has already passed qualification.

### Business Context Layer

The Qualification Agent applies two business context boosts on top of the base noise filter:

**Family Context Boost (+30 score):**
Loaded from `config/family_context.json`. Contains:
- `spouse`: name string
- `children`: list of name strings
- `keywords`: additional family-related terms

Any signal that mentions a family member (by name, in the message or sender) receives a +30 score boost. This ensures family health appointments, school notifications, and family financial messages are never filtered as noise.

**High-Value Domain Boost (+30 score):**
Loaded from `config/high_value_domains.json`. Contains domain categories (medical, legal, financial, travel) with keyword lists. Any signal containing a keyword from a high-value domain receives a +30 score boost.

Scores are capped at 90. A score of 100 is only reachable via the explicit QUALIFIED threshold logic, not by accumulating boosts.

### Rule Engine Integration

`RulesEngine.should_ignore_signal(message)` is called after all basic filters. The rules engine checks against configured ignore patterns (job alerts, news subscriptions, etc.). If the rules engine flags the signal as ignorable, it is REJECTED with reason `LOW_VALUE_SIGNAL`.

### Noise Detection — Rejection Filters (applied in order)

| Priority | Filter | Reason Code | Score |
|---|---|---|---|
| 1 | Age > 90 days (SMS/email) | `STALE_SIGNAL` | 0 |
| 2 | Exact duplicate within 48h | `DUPLICATE_SIGNAL` | 0 |
| 3 | OTP keyword | `OTP` | 10 |
| 4 | WhatsApp system noise | `SYSTEM_NOTIFICATION` | 5 |
| 5 | SMS overlay noise | `SYSTEM_NOTIFICATION` | 5 |
| 6 | Telecom data alerts | `SYSTEM_NOTIFICATION` | 15 |
| 7 | Promotional keywords (if not financial) | `PROMOTION` | 15 |
| 7.5 | Financial advisory (KYC, fraud warnings) | `FINANCIAL_ADVISORY` | 10 |
| 8 | Group/community messages | `LOW_VALUE_SIGNAL` | 45 → REVIEW |
| 9 | Rules Engine ignore match | `LOW_VALUE_SIGNAL` | 15 |

### Qualification Thresholds

Base score: 40
- Family boost: +30
- High-value domain boost: +30
- Maximum before threshold application: 90

| Score | Status |
|---|---|
| ≤ 20 | REJECTED |
| 21–59 | REVIEW |
| ≥ 60 | QUALIFIED |

### Financial Preservation Override

If a signal is about to be REJECTED and the reason code is NOT `STALE_SIGNAL`, `DUPLICATE_SIGNAL`, or `FINANCIAL_ADVISORY`, but the message contains financial preservation keywords (debited, credited, payment, etc.), the status is upgraded from REJECTED to REVIEW with score 25.

This prevents any financial transaction from being silently dropped.

### Review Queue

REVIEW signals are stored in `qualified_signals` with status REVIEW. They do NOT proceed to the SUA automatically. They accumulate in the queue for future user review or manual promotion. This is a known limitation — there is currently no UI for reviewing the REVIEW queue.

### Shadow Mode

The Qualification Agent originally ran in shadow mode alongside the old monolithic pipeline to validate its output before replacing it. Shadow mode is now off — the Qualification Agent IS the pipeline.

### Duplicate Detection

Two-level check:
1. Exact message text match (lowercased, stripped) within any record in the last 48 hours
2. Same source + same sender + same amount match within 48 hours (catches reformatted duplicates)

### Known Limitations

1. WhatsApp signals do not have a reliable age filter (WhatsApp timestamps are unreliable in bulk exports)
2. The REVIEW queue has no UI — reviewed signals must be manually promoted
3. The family context boost is static (loaded from a JSON file, not learned from behavior)
4. Duplicate detection is exact-match — a reformatted version of the same message from the same sender could pass through

### Future Improvements

1. LLM-assisted review queue processing for borderline REVIEW signals
2. Learning-based noise detection that improves from user feedback
3. Dynamic family context updates from Fact Agent outputs

---

## 8. Signal Understanding Agent — Complete Specification

### Deterministic Path

Fires first. Returns a complete contract dict or `None`.

**Currently implemented rules (in order of check):**

1. **Financial Transaction Rule:** Keywords: `debited`, `credited`, `spent`, `spent on`, `card ending`, `received rs`, `received inr`, `amount received`, `amount credited`, `transacted`, `transaction of inr`, `transaction of rs`. Whitespace is normalised before matching (multi-line bank SMS format handled). Classes: `[FINANCIAL]`. Extracts: amount (regex `(?:rs\.?|inr)\s?[\d,]+`), merchant (regex from payee patterns). Routes: `[FinancialAgent]`.

2. **Insurance Payment Receipt Rule:** Insurance payment keywords AND payment receipt confirmation keywords (`received inr`, `receipt no`, `payment received`). Money has moved. Classes: `[FINANCIAL, INFORMATION, ACTION]`. Routes: `[FinancialAgent, TodoAgent, FyiAgent]`. Must check BEFORE insurance renewal rule.

3. **Insurance Renewal/Reminder Rule:** Insurance keywords WITHOUT payment confirmation. Money has NOT moved. Classes: `[INFORMATION, ACTION]`. Routes: `[TodoAgent, FyiAgent]`. NEVER routes to FinancialAgent.

4. **Bill Due Alert Rule:** Keywords: `bill due`, `payment due`, `minimum due`, `outstanding amount`, `card bill`, `bill alert`, `total amount due`. Money has NOT moved. Classes: `[INFORMATION, ACTION]`. Routes: `[TodoAgent, FyiAgent]`. NEVER routes to FinancialAgent.

5. **Delivery Update Rule:** Keywords: `delivered`, `out for delivery`, `courier dispatch`, `amazon order`, `flipkart order`. Classes: `[INFORMATION]`. Routes: `[FyiAgent]`.

6. **Refund Rule:** Keywords: `refund`, `refunded`, `reversed`, `credited back`, `reversal`, `adjusted against`. Two sub-rules:
   - Future-tense refund (`will be refunded`, `pending refund`): Classes `[INFORMATION, ALERT]`. Routes: `[FyiAgent]`. NOT FINANCIAL — money has NOT moved yet.
   - Confirmed refund (no future-tense marker): Classes `[FINANCIAL, INFORMATION]`. Routes: `[FinancialAgent, FyiAgent]`. Money HAS moved.

7. **Medical Appointment Rule:** Keywords: `appointment`, `doctor`, `clinic`, `visit`, `checkup`. Classes: `[INFORMATION, ACTION]`. Routes: `[TodoAgent]`.

8. **Travel Booking Rule:** Keywords: `booking confirmed`, `e-ticket`, `pnr`, `flight`, `hotel reservation`. Classes: `[INFORMATION]`. Routes: `[FyiAgent]`.

### LLM Path

Invoked when deterministic path returns None. Uses a structured prompt with explicit rules:

- Return JSON matching the contract schema
- A signal is FINANCIAL only if money has ALREADY moved (not future tense)
- Future obligations are ACTION or INFORMATION, never FINANCIAL
- Classes are from the canonical set only
- Extract all entities with amounts, merchants, deadlines, people

The LLM response is parsed defensively — all fields get safe defaults if missing. JSON is extracted between first `{` and last `}` to handle markdown formatting. Route mapping is applied programmatically from the classes (the LLM does not determine routes directly).

**Current LLM model:** `qwen3:1.7b` (local, via Ollama). Model is configurable via `settings.local_model`.

### Business Confidence Model

```python
def _calculate_business_confidence(signal, contract, processing_path) -> float:
    # Base
    if processing_path == "RULE_ENGINE":
        base = 1.0
    else:
        base = float(contract.get("confidence") or 0.8)

    # Source reliability
    if trusted_sender in signal.sender:
        base = min(1.0, base + 0.05)
    elif whatsapp_numeric_sender:
        base = max(0.0, base - 0.10)

    # Entity completeness
    if "FINANCIAL" in classes and monetary_value.amount is None:
        base = max(0.0, base - 0.30)

    # Parse quality (LLM path only)
    if processing_path == "LLM" and raw_llm_confidence < 0.75:
        base = max(0.0, base - 0.15)

    return round(base, 4)
```

**Trusted sender fragments:** `hdfcbk`, `sbipsg`, `sbicrd`, `icicibk`, `kotakbk`, `axisbk`, `licind`, `irctc`, `paytm`, `phonepe`, `amazonpay`

**Thresholds:**
- ≥ 0.85: `is_verified = True`, auto-process
- 0.50–0.84: route but flag for human review
- < 0.50: Critical Inbox, hold for review

### Shadow Mode Validation

During development, SUA ran in shadow mode against ~300 real production signals from `scratch/dump_preview.json`. Validation script: `scripts/run_understanding_validation.py`. Results were compared to the legacy pipeline output for alignment. Final alignment achieved: ≥ 95% on all signal types.

### Known Limitations

1. The LLM path can hallucinate merchants or amounts for ambiguous messages
2. WhatsApp group context (who is speaking) is not preserved in the signal — SUA sees only the message text and group name as sender
3. The deterministic path has no learning mechanism — new signal formats require manual rule additions
4. Insurance domain enrichment in the financial transaction rule relies on merchant keyword matching, which can miss obscure insurers

---

## 9. Financial Agent — Complete Specification

### Overview

The Financial Agent is the authoritative processor of all confirmed monetary events. It receives FINANCIAL class contracts from the SUA and produces typed `FinancialFact` records that represent the ground truth of the user's financial history.

Every monetary event that has ever been processed by Jarvis has one and exactly one `FinancialFact`. The lineage is complete and traceable.

### Internal Transfer Detection — The 4-Condition Algorithm

Internal transfers are movements between the user's own accounts (HDFC savings → SBI savings). They appear in the signal stream as a debit from one account and a credit to another. If not detected and excluded, they inflate both spending AND income figures.

**Why amount-only detection fails:** A ₹2,000 Zomato payment and a ₹2,000 salary partial credit in the same week would match. A ₹909 refund and a ₹909 insurance premium would match. Amount-only matching produces false positives.

**The 4-Condition Algorithm — all four must be satisfied:**

```
Condition 1 — Amount match:
  |D.amount - C.amount| < ₹1  (rounding tolerance)

Condition 2 — Account ownership validation:
  Both legs resolve to KNOWN_ACCOUNT_ALIASES
  (hdfc, hdfcbk, sbi, sbipsg, icici, axis, kotak, yono, etc.)
  Prevents external payments from matching internal transfers

Condition 3 — Transfer indicator present:
  Message contains at least ONE of:
  [IMPS, NEFT, RTGS, UPI transfer, fund transfer, transfer to,
   transfer from, moved to, a/c credited, YONO,
   net banking transfer, online transfer, money transfer]

Condition 4 — Time window (typed by transfer type):
  IMPS:       ≤ 30 minutes
  UPI:        ≤ 10 minutes
  NEFT:       ≤ 4 hours
  RTGS:       ≤ 2 hours
  YONO:       ≤ 48 hours
  UNKNOWN:    ≤ 48 hours (default)
  Window = min(debit_window, credit_window)
```

**When detected:** Both legs get `fact_type = INTERNAL_TRANSFER`, `is_excluded_from_accounting_spend = True`. A `transfer_pairs` record links the two legs. Neither leg is counted in any spending total.

**Why this belongs ONLY in the Financial Agent:** Internal transfer detection requires access to both debit and credit financial events simultaneously, plus the `bank_accounts` / `known_account_aliases` registry. No other agent has this context. The SUA sees individual signals — it cannot see the matched pair. The Qualification Agent sees individual signals at different times. Only the Financial Agent, which processes all FINANCIAL class signals and has access to the complete event history, can reliably detect the pair.

### Salary Detection — The 4-Tier Algorithm

```
Tier 1 — Keyword match (confidence: 0.95):
  message contains: salary, sal cr, sal credit, monthly salary,
                    basic pay, net pay, payroll, sal/cr, salary credit
  → fact_type = INCOME_SALARY, confidence = 0.95

Tier 2 — Salary source registry match (confidence: 0.90):
  credit.sender_alias ∈ salary_source.aliases
  AND credit.day_of_month within (expected_day ± tolerance)
  AND |credit.amount - expected_amount| / expected_amount ≤ amount_tolerance_pct
  → fact_type = INCOME_SALARY, confidence = 0.90
  → update salary_source.last_seen, detection_history

Tier 3 — Recurring credit pattern (confidence: 0.80):
  Same sender_alias sent a credit on approximately the same day
  in ≥ 3 of the last 4 months
  AND amount variation ≤ 15%
  → fact_type = INCOME_SALARY_CANDIDATE
  → create new salary_source entry (is_active = False, pending_review = True)

Tier 4 — Large unmatched credit (confidence: 0.50):
  credit.amount ≥ ₹20,000
  AND no internal transfer match
  AND no salary source match
  AND no refund context
  → fact_type = INCOME_UNCLASSIFIED
  → flag for manual review
```

**Salary Source Registry (`salary_sources` table):** Stores known employers with aliases, expected day-of-month, expected amount, and amount tolerance. The registry starts empty at V2 launch and grows from Tier 3 candidate promotions. When a Tier 3 candidate is confirmed by the user, `is_active` is set to True and Tier 2 will match it from the next month.

### Refund Logic

**Decision (locked):** Refunds are not income. Refunds offset prior spending.

A refund of ₹450 from Zomato means the user did not actually spend ₹450 at Zomato. Treating it as income would: inflate income, double-count (the original expense + the refund cancel each other), and misrepresent the true cost of the month.

**Refund Processing Algorithm:**
1. Create `FinancialFact` with `fact_type = REFUND_EVENT`
2. Search for originating EXPENSE_EVENT: matching merchant + amount within 30 days prior
3. If found: link via `refund_of_fact_id`, set originating fact `is_refunded = True`, apply `refund_applied_to_month` = original expense month
4. If not found: record with `refund_of_fact_id = null`, apply offset to current month `OTHER` category
5. NEVER add refund amount to income totals
6. NEVER add refund amount to credit_received totals

**Edge cases:**
- Refund in a different month than original expense: offset applied to ORIGINAL expense month
- Partial refund: offset only the refund amount
- Multiple refunds for same merchant: match greedily to most recent matching expense
- Future-tense refund promise: intercepted by SUA, classified as `[INFORMATION, ALERT]`, never reaches Financial Agent

### Merchant Registry

**Pre-seeded list (24 canonical merchants, 45+ aliases):**

| Category | Merchants |
|---|---|
| FOOD_DINING | Zomato, Swiggy |
| GROCERIES | BigBasket, Zepto, Blinkit |
| MEDICAL | Apollo Pharmacy, MedPlus |
| UTILITIES | Airtel, Jio, TNEB |
| ENTERTAINMENT | Netflix, Spotify, Amazon Prime, Hotstar |
| SHOPPING | Amazon, Flipkart |
| TRANSPORT | Ola, Uber, Rapido |
| TRAVEL | IRCTC, MakeMyTrip |
| INSURANCE | Coverfox, LIC |
| BILL_PAYMENT | SBI Card, HDFC Card |
| INVESTMENT | Zerodha, Groww, and 9 mutual fund houses |

**Merchant resolution order:**
1. Pre-seeded registry (substring match against lowercased text) → confidence 1.0
2. Rules Engine dynamic rules (user overrides + learned mappings) → confidence 1.0
3. Heuristic keyword checks (fish, mutton, vegetables) → confidence 1.0
4. LLM classification (cached by SHA-256 hash of search text) → confidence 0.9

**Automatic promotion:** When an unclassified merchant appears ≥ 3 times, it is queued for auto-categorisation if its name fuzzy-matches a known category keyword.

### Accounting Spend vs Lifestyle Spend

This split is fundamental to the V2 financial model. A single spending total conceals the user's actual financial behaviour.

**Accounting Spend** — "How much money left my accounts this month?"
```
Accounting Spend = SUM(all DEBIT facts for the month)
                 − SUM(INTERNAL_TRANSFER debit legs)
```
Includes: lifestyle expenses, insurance premiums, investments, bill payments, subscriptions
Excludes: internal transfers only

This is the complete picture of outflows. Used for net cashflow calculation.

**Lifestyle Spend** — "How much did I actually spend on living this month?"
```
Lifestyle Spend = Accounting Spend
               − SUM(INVESTMENT facts)
               − SUM(INSURANCE_PAYMENT facts)
               − SUM(BILL_PAYMENT_CC facts)
```
Includes: food, groceries, transport, entertainment, medical, utilities, shopping
Excludes: investments, insurance premiums, credit card payments (the underlying card expenses are already in Lifestyle Spend from when the card was used)

**Net Cashflow** = Total Income − Accounting Spend

### Monthly Rollups

Computed by AggregationService (not Financial Agent). See Section 3.6.

**`monthly_spending_summary` fields (V2):**
- `accounting_spend`: all debits excl. internal transfers
- `lifestyle_spend`: day-to-day living only
- `total_income`: salary + other confirmed income
- `net_cash_flow`: income − accounting_spend
- `internal_transfers`: tracked for transparency
- `insurance_premiums`: tracked separately
- `investments`: tracked separately
- `refund_offsets`: total refunds applied to spending this month
- `transaction_count`: number of debit events included

**`monthly_category_spend` fields:**
- `month_key`: YYYY-MM
- `category_name`: FOOD_DINING, GROCERIES, etc.
- `amount`: total spend in category for month
- `transaction_count`: number of transactions in category

### Trend Generation

MoM trends computed by AggregationService from `monthly_category_spend` records. For each category in the current month, the prior month's amount is fetched and the percentage change is computed.

`change_percentage = ((current − previous) / previous) × 100`

If no prior month data exists: `change_percentage = 0.0`

### Financial Confidence Model

The Financial Agent uses the SUA's business confidence score from the contract. A contract with `confidence < 0.85` is processed but flagged as requiring review. High-confidence facts (from RULE_ENGINE path, trusted bank senders) are auto-processed without review.

### Financial Boundaries (Permanent, Locked)

1. **Financial Agent receives ONLY FINANCIAL class contracts.** If `"FINANCIAL" not in contract["classes"]`, the Financial Agent returns None immediately and does nothing.
2. **Financial Agent does NOT reclassify the SUA contract.** The signal type and classes set by SUA are authoritative.
3. **Financial Agent does NOT write to SUA tables.** It writes only to its own owned tables.
4. **Money not yet moved = not FINANCIAL.** Bill due alerts, insurance renewal reminders, "your EMI will be deducted" notices are not processed by the Financial Agent.
5. **Refunds reduce spending, never increase income.**
6. **Internal transfer legs are not spending.** Both legs (debit and credit) are excluded from all spend computations.
7. **Aggregation is AggregationService's job.** Financial Agent writes facts. AggregationService computes rollups.

---

## 10. Locked Architectural Decisions

These decisions are permanent. They may not be revisited without explicit approval from the product owner. Each was made for documented reasons. Each has been validated against real data.

### AD-1: Qualification Before LLM

**Decision:** No signal is sent to the LLM before passing qualification.

**Rationale:** LLMs are expensive (latency, compute). Roughly 60–70% of all raw signals are OTPs, promotional messages, system notifications, or stale records. Sending these to the LLM wastes resources and pollutes the output.

**Locked:** Yes. Any implementation that bypasses qualification to send raw signals to the LLM is architecturally incorrect.

---

### AD-2: Deterministic Before LLM (within SUA)

**Decision:** The deterministic path is always attempted first. LLM is only invoked when deterministic returns None.

**Rationale:** Bank SMS formats are standardised. Insurance SMS formats are standardised. For these known patterns, a regex is 100% reliable and zero-latency. Using LLM for known patterns is strictly worse on every metric.

**Locked:** Yes. Any new signal type that has a reliable pattern should be implemented as a deterministic rule, not an LLM prompt extension.

---

### AD-3: One Owner Per Table

**Decision:** Every database table has exactly one service that writes to it. No exceptions.

**Rationale:** Multiple writers create race conditions, data integrity issues, and debugging nightmares. If two services both write to `financial_facts`, a bug in either one can produce incorrect facts and there is no reliable way to determine which service caused it.

**Locked:** Yes. If a new service needs to write data, it gets its own table. It does not share a table with another service.

---

### AD-4: Financial Agent Owns All Financial Tables

**Decision:** The Financial Agent is the sole writer to `financial_events`, `financial_facts`, `bank_accounts`, `transfer_pairs`, `salary_sources`, `salary_events`, `merchants`, `merchant_profiles`.

**Rationale:** Financial correctness depends on a single authoritative source. If the SUA or AggregationService wrote to `financial_facts`, it would be impossible to guarantee the integrity of the fact ledger.

**Locked:** Yes.

---

### AD-5: Aggregation Service Owns All Rollup Tables

**Decision:** AggregationService is the sole writer to `monthly_spending_summary`, `monthly_category_spend`, `monthly_category_trends`.

**Rationale:** Rollups must be idempotent and re-runnable. This requires a clean separation from the fact-writing path. If Financial Agent wrote rollups as part of fact writing, a bug in rollup logic would be entangled with fact writing.

**Locked:** Yes.

---

### AD-6: SUA Never Computes Money

**Decision:** The Signal Understanding Agent does not compute financial totals, category rollups, or spending summaries. It produces contracts.

**Rationale:** Financial computation requires the full history of events, knowledge of the user's accounts, salary sources, and merchant registry. The SUA sees one signal at a time. It does not have the context to make financial computations correctly.

**Locked:** Yes.

---

### AD-7: Refunds Offset Expenses, Never Inflate Income

**Decision:** A confirmed refund credit reduces prior spending in the original expense month. It is never added to income.

**Rationale:** A refund is a correction of a prior expense. Including it in income would double-count the original expense (once as spending, once as income offset) and misrepresent the user's actual income.

**Locked:** Yes. The FinancialFact schema enforces this — `REFUND_EVENT` facts have `is_excluded_from_accounting_spend = True` and a `refund_of_fact_id` linking to the original expense.

---

### AD-8: Internal Transfers Are Excluded from All Spending

**Decision:** Both legs of an internal transfer (debit + credit) are excluded from accounting_spend, lifestyle_spend, and income.

**Rationale:** Moving money between the user's own accounts does not change their net worth. Including it would inflate both sides of the ledger.

**Locked:** Yes. The 4-condition algorithm is designed to produce zero false positives. A transfer detected incorrectly is excluded from spending, which is the safer failure mode (slightly undercounting spend) compared to including it (double-counting spend for genuine transfers).

---

### AD-9: Supabase Is the Source of Truth

**Decision:** Supabase PostgreSQL is the canonical data store. SQLite is a runtime cache.

**Rationale:** Supabase provides persistent, queryable, remotely accessible storage. SQLite is local and fast but not accessible from external systems (the UI, monitoring, the Android app). All production queries against the user's data read from Supabase.

**Locked:** Yes. Any new table that needs to be queried by the UI or external systems is a Supabase table.

---

### AD-10: SQLite Is the Runtime Cache

**Decision:** SQLite stores intermediate pipeline state (raw signals, qualified signals) for fast local access during pipeline execution. It is not the source of truth.

**Rationale:** The pipeline runs locally. Reading from and writing to Supabase for every intermediate signal would be slow and network-dependent. SQLite provides fast local access during execution, with Supabase sync on completion.

**Locked:** Yes. SQLite records are not relied upon for long-term data integrity. They can be rebuilt from Supabase if needed.

---

### AD-11: The FINANCIAL Class Boundary Is Inviolable

**Decision:** A signal receives the FINANCIAL class only if money has already moved. Future obligations are not FINANCIAL.

**Rationale:** The Financial Agent persists facts about real monetary events. If it receives a future obligation (bill due alert, insurance renewal reminder), it would record a financial event that has not occurred. This corrupts the spending record.

**Locked:** Yes. This rule is implemented in the SUA's deterministic path (rules 3 and 4 explicitly exclude future obligations from FINANCIAL class) and documented in the LLM prompt.

---

### AD-12: Merchant Registry Is Pre-Seeded

**Decision:** The merchant registry ships with a pre-built seed list of 24 canonical merchants.

**Rationale:** An empty registry on first run produces 100% `OTHER` category classification. This is useless. The seed list ensures meaningful classification from the first pipeline execution.

**Locked:** Yes. The seed list lives in `FinancialClassifier.MERCHANT_SEED`.

---

### AD-13: AggregationService Is Idempotent

**Decision:** Re-running AggregationService on the same data always produces the same result.

**Rationale:** If aggregation is not idempotent, running it twice will double all totals. The pipeline must be safely re-runnable after failures without manual cleanup.

**Implementation:** Aggregation clears the rollup tables before rebuilding, then uses upsert (not insert) for all writes.

**Locked:** Yes.

---

## 11. Validation History

### Validation 1 — Qualification Agent

**Date:** Early 2026 (Phase 1)
**Data:** ~300 real SMS/WhatsApp/email signals from production
**Methodology:** Manually reviewed all QUALIFIED signals for false positives; all REJECTED signals for false negatives
**Results:**
- OTP rejection: 100% correct
- WhatsApp system noise rejection: 100% correct
- Promotional rejection: 2 false positives (financial-sounding promotional SMS) — fixed by checking for transaction keywords before applying promotional rejection
- Telecom data alerts: 100% correct
- Financial preservation override: 100% correct (no financial signal silently dropped)
**Status:** Passed. Qualification Agent went live.

### Validation 2 — Business Context Layer

**Date:** Phase 1, post-family-context implementation
**Data:** Production signals containing family names, medical terms, school references
**Results:**
- Family context boost correctly promoted low-scoring family messages to QUALIFIED
- High-value domain boost correctly promoted medical appointment SMS to QUALIFIED
**Status:** Passed.

### Validation 3 — Signal Understanding Agent (Shadow Mode)

**Date:** Phase 2
**Data:** `scratch/dump_preview.json` — real production signals
**Methodology:** SUA ran in shadow mode alongside legacy pipeline. Output contracts compared against expected classification from legacy system.
**Results:**
- Financial transaction detection: aligned with legacy on all bank SMS formats tested
- Insurance renewal → correctly NOT FINANCIAL (legacy had incorrectly included them)
- Bill due alerts → correctly NOT FINANCIAL (legacy had incorrectly included them)
- Refund signals → correctly FINANCIAL (legacy had routed to FyiAgent only)
- Business confidence model: thresholds calibrated against real output
**Alignment achieved:** ≥ 95%

### Validation 4 — Semantic Hardening (6 Fixes)

**Date:** 2026-06-24 (Conversation 1a24a9fe)
**Problem:** Six semantic errors discovered in SUA deterministic path:
1. Insurance renewals incorrectly routed to FinancialAgent (money not moved)
2. Bill due alerts incorrectly routed to FinancialAgent
3. Refund keyword coverage too narrow (only "refund", missed "reversed", "credited back")
4. Credit/deposit keywords too narrow (missed "received inr", "amount credited")
5. LLM prompt lacked explicit FINANCIAL boundary rule for future obligations
6. `_calculate_business_confidence()` method was missing (runtime AttributeError on every signal)

**Fixes implemented:** All 6 fixed in `signal_understanding_agent.py`

**Validation:** `scripts/run_understanding_validation.py` run against production data — all 6 fixes verified.

### Validation 5 — Financial Agent V2 Revision

**Date:** 2026-06-25 (Current conversation)
**Changes validated:**
- `financial_classifier.py`: pre-seeded merchant registry (45+ aliases), expanded category taxonomy, `is_lifestyle_category()` helper
- `supabase_repo.py`: `save_monthly_spending_summary_v2()`, `save_transfer_pair()`, `fetch_financial_events_by_month()`, `fetch_financial_events_by_subtype()`, `update_monthly_category_spend_with_refund()`
- `financial_aggregator.py`: 4-condition transfer detection, 4-tier salary detection, refund offset processing, Accounting/Lifestyle spend split, `AggregationService` class

**Syntax verification:** `python3 -m py_compile` on all three files — ALL PASS.

### Major Bugs Fixed

| Bug | Module | Impact | Fix |
|---|---|---|---|
| Insurance renewals → FinancialAgent | SUA | Money-not-moved events incorrectly recorded as financial facts | Rule 3 — insurance renewals explicitly excluded from FINANCIAL class |
| Bill due alerts → FinancialAgent | SUA | Same as above | Rule 4 — bill alerts explicitly excluded from FINANCIAL class |
| `_calculate_business_confidence()` missing | SUA | Runtime AttributeError on every signal, pipeline crashed | Method implemented per spec |
| Amount-only internal transfer detection | FinancialAggregator | False positives — coincidental same-amount transactions mis-flagged | 4-condition algorithm implemented |
| Refunds counted as income | FinancialAggregator | Income figures inflated by refund amounts | Refund-as-offset semantics implemented |
| Empty merchant registry on first run | FinancialClassifier | 100% EXPENSE_UNCLASSIFIED on first execution | 24-merchant pre-seeded registry implemented |
| Single spending total | FinancialAggregator | Investments, insurance, CC payments indistinguishable from lifestyle | Split into Accounting Spend + Lifestyle Spend |
| STALE whitespace in bank SMS | SUA deterministic | "Received!\nINR 2,500" — newline broke keyword match for "received inr" | `re.sub(r'\s+', ' ', msg_lower)` normalisation applied before matching |

### Lessons Learned

1. **Deterministic path bugs are cheaper than LLM bugs.** A wrong regex is testable and fixable. A wrong LLM prompt manifests differently across different inputs.
2. **Shadow mode is essential.** Every major module was validated in shadow mode before going live. The SUA shadow run caught 3 of the 6 semantic errors before they reached production.
3. **The financial boundary rule is the hardest to get right.** The FINANCIAL class assignment is the most consequential decision in the pipeline. Getting it wrong cascades through the entire system.
4. **Idempotency is not optional.** The pipeline runs on a schedule. It will run multiple times on the same data. Every module must be safe to re-run.
5. **Pre-seeding avoids cold-start failures.** Starting with an empty merchant registry is a user experience disaster. Pre-seeding is mandatory.

---

## 12. Remaining Roadmap

### Module 4 — Financial Agent (Current — Partially Complete)

**Completed:**
- [x] Financial event persistence
- [x] 4-condition internal transfer detection
- [x] 4-tier salary detection
- [x] Refund event processing (offset semantics)
- [x] Pre-seeded merchant registry (24 merchants)
- [x] Accounting Spend vs Lifestyle Spend split
- [x] AggregationService ownership split
- [x] Financial fact model with full lineage
- [x] MoM trend generation

**Remaining:**
- [ ] Supabase migration: create `transfer_pairs` table (currently graceful no-op)
- [ ] Supabase migration: create `salary_source` table (currently graceful no-op)
- [ ] Add `transaction_subtype` column to `financial_events` in Supabase
- [ ] User-facing flow for confirming Tier 3 salary candidates (INCOME_SALARY_CANDIDATE → INCOME_SALARY)
- [ ] User-facing flow for confirming auto-promoted merchant entries
- [ ] `financial_intelligence.py` (SQLAlchemy path) alignment to V2 model — this file still uses old single-spend-total model
- [ ] Real-time aggregation trigger vs nightly schedule decision (currently nightly)
- [ ] Merchant registry growth via automatic promotion (appears ≥ 3 times → auto-categorise)
- [ ] Financial anomaly detection (category spend > 150% prior month → alert)

### Module 5A — Todo Agent

**Not started.**

**Required:**
- [ ] Design Todo Agent contract consumption pattern
- [ ] Implement deadline extraction from contract entities
- [ ] Implement priority mapping from importance field
- [ ] Implement duplicate todo detection (same signal should not create two todos)
- [ ] Supabase schema for `todos` table (partially exists — needs validation)
- [ ] Validation against real ACTION class contracts

### Module 5B — FYI Agent

**Not started.**

**Required:**
- [ ] Design FYI Agent contract consumption pattern
- [ ] Implement FYI event creation from INFORMATION class contracts
- [ ] `read_flag` management (mark as read from UI)
- [ ] Supabase schema validation for `fyi_events`

### Module 5C — Fact Agent

**Not started.**

**Required:**
- [ ] Design entity-attribute fact schema
- [ ] Implement fact extraction from MEMORY class contracts
- [ ] Design fact deduplication (same entity, same attribute — update vs. create new)
- [ ] Supabase schema for `facts` table

### Module 6 — Daily Brief Agent

**Not started.**

**Required:**
- [ ] Design brief structure (financial snapshot + todo summary + info highlights + anomalies)
- [ ] Implement LLM-based prose generation (all computation done before LLM is called)
- [ ] Implement push notification delivery (Android)
- [ ] Streamlit UI integration for brief display

### Android Integration

**Not started.**

**Required:**
- [ ] Android app that intercepts SMS at OS level (broadcast receiver)
- [ ] WhatsApp message forwarding mechanism
- [ ] Direct API push to Consumer instead of file-based ingestion
- [ ] Real-time pipeline trigger on signal receipt

### UI Redesign

**Current:** Streamlit dashboard (`ui/` directory)

**Remaining:**
- [ ] Financial dashboard: accounting_spend vs lifestyle_spend view
- [ ] Monthly trend charts per category
- [ ] Salary detection review queue
- [ ] Merchant registry management
- [ ] Todo management (complete/snooze/dismiss)

---

## 13. Engineering Principles

These principles governed every architectural decision in Jarvis. They should govern every future decision.

### P-1: LLMs Interpret. Agents Own Business Logic.

An LLM can classify a message. It cannot own the rule that says "a refund is not income." That rule is implemented in code, tested against real data, and locked. If the rule were inside the LLM prompt, it could be overridden by prompt variations, model upgrades, or context shifts.

Business logic lives in code. LLMs are used for interpretation of unstructured text.

### P-2: Deterministic First

Every processing step that can be done deterministically (regex, keyword match, rule engine) must be done deterministically before invoking an LLM. Deterministic = 100% reproducible, zero latency, zero cost, fully testable. LLM = probabilistic, latency, cost, partially testable.

### P-3: Quality Over Speed

A module that is not validated is not complete. Every module requires:
1. A validation dataset (real production data)
2. A validation script
3. A validation report documenting what was tested and what passed

Shipping an unvalidated module is worse than shipping no module.

### P-4: One Responsibility Per Agent

Each agent does exactly one thing. The Qualification Agent qualifies. The SUA understands. The Financial Agent produces financial facts. The Aggregation Service computes rollups.

When an agent starts doing two things, extract one responsibility into a new agent.

### P-5: Idempotent Pipelines

Every module must produce the same output when run twice on the same input. The pipeline may fail partway through. It must be restartable without corrupting data. This means:
- All writes use upsert, not insert, where appropriate
- Rollup computations clear before rebuilding
- Fact writing checks for existing records before creating new ones

### P-6: Replayable Events

Every fact in the system traces back to the raw signal that caused it. The lineage chain is: `financial_facts` → `financial_events` → `understood_signals` → `qualified_signals` → `mobile_signals`. A fact can always be re-derived from its source signal. If the classification algorithm is improved, facts can be re-generated by replaying signals through the new algorithm.

### P-7: No Hidden State

Every decision made by every agent is recorded. The Qualification Agent records the score and reason code for every signal. The SUA records the processing path (RULE_ENGINE or LLM) and confidence for every contract. The Financial Agent records the classification method and confidence for every fact. Hidden state is a debugging anti-pattern.

### P-8: No Duplicate Ownership

If two agents can write to the same table, neither owns that table. This is a contradiction. Ownership is exclusive. See AD-3.

### P-9: Fail Loudly, Degrade Gracefully

Supabase failures are graceful (log + continue). SQLite failures are fatal (abort the run). LLM failures produce a default safe-fallback contract. Classification failures fall back through the resolution chain (seed → rules engine → LLM → OTHER). No failure silently produces wrong data.

### P-10: Real Data Only for Validation

Synthetic signals are never used for validation. Only real production signals from the actual Android device are used. Synthetic signals do not reflect the real-world variety and edge cases of Indian bank SMS formats, WhatsApp group messages, and IMAP email parsing.

---

## 14. Known Technical Debt

This is an honest record of every intentional shortcut. These items are not bugs — they are deferred work that was consciously traded against time.

### TD-1: Shadow Mode Left Active

**What:** The SUA still has a `run_shadow_mode()` method that runs against `QualifiedSignal` records in SQLite. This was the validation mechanism during development.

**Problem:** Shadow mode will continue to consume compute if called. It is no longer needed.

**Planned resolution:** Remove `run_shadow_mode()` when the SUA is fully integrated into the main pipeline and shadow mode validation is complete.

---

### TD-2: Legacy Pipeline (`signal_processor.py`) Not Decommissioned

**What:** `services/signal_processor.py` (28,021 bytes) contains the original monolithic classification logic. It is still importable and may still be called from the orchestrator.

**Problem:** It implements the old single-spend-total model, lacks the 4-condition transfer algorithm, and predates the canonical contract format.

**Planned resolution:** Audit the orchestrator's call chain. Remove all calls to `SignalProcessor`. Decommission the file.

---

### TD-3: `financial_intelligence.py` Not Aligned to V2 Model

**What:** `services/financial_intelligence.py` uses the SQLAlchemy path and still implements the old 3-condition transfer detection, single spending total, and lacks salary detection and refund semantics.

**Problem:** This file may be called from the orchestrator in certain run paths.

**Planned resolution:** Rewrite `financial_intelligence.py` to mirror the V2 logic in `financial_aggregator.py`, or remove it if the SQLAlchemy path is fully replaced by the Supabase path.

---

### TD-4: `transfer_pairs` Table Not Yet Created in Supabase

**What:** The `FinancialAggregator` calls `SupabaseRepo.save_transfer_pair()`, which gracefully no-ops if the table doesn't exist.

**Planned resolution:** Create the Supabase migration:
```sql
CREATE TABLE jarvis_insights_schema.transfer_pairs (
  pair_id UUID PRIMARY KEY,
  debit_event_id UUID NOT NULL,
  credit_event_id UUID NOT NULL,
  amount DECIMAL NOT NULL,
  currency TEXT DEFAULT 'INR',
  transfer_type TEXT,
  confidence FLOAT,
  window_used_seconds INTEGER,
  detected_at TIMESTAMPTZ DEFAULT now()
);
```

---

### TD-5: `salary_source` Table Not Yet Created in Supabase

**What:** The salary detection algorithm queries the `salary_source` table. It gracefully returns an empty list if the table doesn't exist.

**Planned resolution:** Create the Supabase migration for `salary_source`. Seed with any known employer aliases for the user.

---

### TD-6: `transaction_subtype` Column Not Yet on `financial_events`

**What:** `SupabaseRepo.fetch_financial_events_by_subtype()` queries by `transaction_subtype`. The column may not exist yet in Supabase.

**Planned resolution:** Add column via Supabase migration.

---

### TD-7: Review Queue Has No UI

**What:** Signals that score 21–59 are placed in REVIEW status in `qualified_signals`. There is no user interface for reviewing, approving, or rejecting these signals.

**Planned resolution:** Add a Review Queue tab to the Streamlit UI. Allow user to: QUALIFY (promote to processing), REJECT (mark as noise), or IGNORE (keep in REVIEW).

---

### TD-8: No Real-Time Aggregation Trigger

**What:** AggregationService runs at the end of the pipeline (nightly schedule). There is no per-signal trigger.

**Planned resolution:** V3 will implement an event bus pattern where each Financial Agent fact write emits a `fact_written` event that triggers incremental aggregation.

---

### TD-9: Merchant Learning Is Static

**What:** The merchant registry grows only through pre-seeded entries, manual user confirmation, and the 3-appearance auto-promotion rule. There is no ML-based merchant learning.

**Planned resolution:** Future LearningEngine integration. After sufficient transaction history, merchant classification patterns can be learned from confirmed user corrections.

---

### TD-10: Salary Source Registry Is Empty at Launch

**What:** The `salary_source` registry starts empty. Tier 2 salary detection is therefore inactive until Tier 3 candidates are confirmed by the user.

**Planned resolution:** During user onboarding, bootstrap the registry from the first 3 months of transaction history (a one-time historical analysis pass).

---

### TD-11: Android Integration Is File-Based

**What:** The Consumer reads signal files exported from the Android device. It does not receive signals in real time.

**Planned resolution:** An Android app that intercepts SMS at OS level and pushes directly to the Jarvis Consumer API. Removes the manual export step.

---

### TD-12: No Event Bus

**What:** Agents communicate by direct method calls and shared database reads. There is no message queue or event bus.

**Planned resolution:** For V3+ scale, an event bus (Redis Streams, or a simple SQLite-backed queue) would allow agents to run asynchronously and in parallel. Currently, the sequential pipeline is sufficient.

---

## 15. Repository Navigation Guide

### Root Directory Structure

```
/home/prad/petprojects/ai/jarvis/
├── services/          ← ALL AGENT IMPLEMENTATIONS
├── storage/           ← DATABASE LAYER (models + repositories)
├── orchestration/     ← PIPELINE ORCHESTRATOR + SCHEDULER
├── consumer/          ← RAW SIGNAL INGESTION
├── ingestion/         ← FILE INGESTION (email, SMS exports)
├── intelligence/      ← LLM ROUTING (IntelligenceRouter)
├── configs/           ← SETTINGS, CONSTANTS
├── config/            ← JSON CONFIGURATION FILES (family_context, rules, domains)
├── api/               ← REST API (FastAPI or equivalent)
├── app/               ← APPLICATION ENTRY POINTS
├── ui/                ← STREAMLIT DASHBOARD
├── scripts/           ← VALIDATION SCRIPTS, UTILITIES
├── tests/             ← TEST SUITE
├── docs/              ← THIS DOCUMENT AND OTHER DOCUMENTATION
├── scratch/           ← DEVELOPMENT SCRATCH FILES (not production)
└── data/              ← LOCAL DATA FILES (signal exports, etc.)
```

### Key Files by Purpose

| Purpose | File |
|---|---|
| Pipeline entry point | `services/pipeline_orchestrator.py` |
| Qualification Agent | `services/signal_qualification_agent.py` |
| Signal Understanding Agent | `services/signal_understanding_agent.py` |
| Financial Agent (primary) | `services/financial_agent.py` |
| Financial Aggregator + AggregationService | `services/financial_aggregator.py` |
| Financial Classifier (merchant registry) | `services/financial_classifier.py` |
| Rules Engine | `services/rules_engine.py` |
| Supabase data access | `services/supabase_repo.py` |
| LLM routing | `intelligence/routing/router.py` |
| All DB models (SQLAlchemy) | `storage/models/` |
| Settings | `configs/settings.py` |
| Task type constants | `configs/constants.py` |
| Family context config | `config/family_context.json` |
| High-value domains config | `config/high_value_domains.json` |
| Qualification rules config | `config/qualification_rules.json` |

### How a New Engineer Should Approach This Project

**Day 1: Read this document entirely.** Do not look at code first. Understand the architecture, the decisions, and the ownership model. Everything in the code is a consequence of what is in this document.

**Day 2: Read the key agent files.** In order:
1. `services/signal_qualification_agent.py` — understand the input filter
2. `services/signal_understanding_agent.py` — understand the contract format
3. `services/financial_agent.py` — understand fact production
4. `services/financial_aggregator.py` — understand rollup computation

**Day 3: Run the validation scripts.** Before making any change, ensure the existing validation passes:
```bash
cd /home/prad/petprojects/ai/jarvis
python scripts/run_understanding_validation.py
```

**Before implementing anything new:**
1. Identify which agent owns the relevant domain
2. Confirm the change does not violate any locked architectural decision (Section 10)
3. Write a plan document and get approval before writing code
4. After implementation, run validation and produce a validation report

**The golden rule:** If you are not sure which agent owns a function, the answer is in the Database Ownership Matrix (Section 5). The owner of the output table is the owner of the function.

---

## 16. Resume Instructions for Any Future LLM

**This section is addressed directly to any AI model that reads this document.**

---

### Read This Document First

Before you write a single line of code, before you ask a clarifying question, before you propose a design — read this entire document. It was produced at the cost of months of iteration and contains every decision, every lesson, and every constraint that governs this project.

Do not skim it. Do not summarise it before reading it. It is already a summary. Read the full text.

---

### Do Not Redesign Existing Modules

The Qualification Agent, Signal Understanding Agent, Financial Agent, and Aggregation Service are designed, validated, and locked. Do not propose alternative architectures for these modules unless the product owner explicitly asks you to.

If you think you see a better way to structure internal transfer detection, or a better way to classify expenses, or a better confidence model — record the thought and ask whether the product owner wants to discuss it. Do not implement it unilaterally.

---

### Respect Locked Architectural Decisions

Section 10 documents 13 locked decisions. These are not suggestions. They are constraints.

If your implementation requires violating AD-3 (One Owner Per Table), stop. Your implementation is wrong. Find a different approach.

If your implementation routes a bill due alert to the Financial Agent, stop. Your implementation violates AD-11. A bill due alert is not a monetary event.

If your implementation counts a refund as income, stop. Your implementation violates AD-7.

---

### Validate Before Implementing

Every new module requires:
1. A written design document (what it does, what tables it owns, what it must never do)
2. Approval from the product owner
3. Implementation
4. Validation against real production data
5. A validation report

Do not skip steps 1–2. Do not skip step 5.

---

### Never Move Business Logic Between Agents

If a rule currently lives in the Financial Agent, it stays in the Financial Agent. If a rule lives in the SUA, it stays in the SUA. Moving business logic between agents creates ownership ambiguity, breaks the single-responsibility principle, and can produce subtle correctness errors that are hard to trace.

The only exception is if the product owner explicitly approves a module boundary change, with full documentation of why the change is being made and what its impact on the database ownership matrix is.

---

### Do Not Bypass Deterministic Processing

If you identify a new signal type that should be handled, implement it as a deterministic rule in the SUA first. Only implement it as an LLM prompt extension if the signal type is genuinely ambiguous and cannot be reliably detected with keywords or regex.

---

### Do Not Introduce New Ownership Conflicts

Before adding a write operation to any service, verify that the target table is owned by that service in the Database Ownership Matrix (Section 5). If the table is owned by a different service, you have two options:
1. Use the owning service's public API to perform the write
2. Ask the product owner whether a new table should be created for this data

There is no option 3 (write to a table you don't own).

---

### Preserve Backward Compatibility

If you change a table schema or a method signature, ensure that all existing consumers of that table or method continue to work. The `save_monthly_spending_summary_v2()` method was added alongside the original `save_monthly_spending_summary()` (not replacing it) specifically to preserve backward compatibility with existing consumers.

Unless the product owner explicitly approves a breaking change, always add, never replace.

---

### Every Implementation Must End with a Validation Report

After every implementation task, produce a document (or update `walkthrough.md`) that records:
- What was changed and why
- What validation was performed
- What passed
- What failed (and what was done about it)
- What known limitations remain

A change without a validation report is incomplete.

---

### The Most Important Thing

This system processes real financial data about a real person. Errors in the Financial Agent are not bugs — they are incorrect statements about the user's financial life. A refund counted as income means the user's income figures are wrong. A spending category miscategorised means the spending breakdown is wrong. A salary missed means the net cashflow is wrong.

Hold the financial layer to the highest standard. If you are not confident a change is correct, do not ship it. Validate it first.

Quality is the product. Correctness is not optional.

---

*End of Jarvis AI OS Architectural Anchor Document*
*Created: 2026-06-25 · Version 1.0*
*Next review: after Module 5 (Todo Agent + FYI Agent) completion*
