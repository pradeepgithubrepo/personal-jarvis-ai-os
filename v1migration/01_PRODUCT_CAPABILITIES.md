# Jarvis V1 — Product Capabilities Inventory

> Migration Knowledge Base · Document 01  
> Produced: 2026-07-04 · Source: Full V1 codebase analysis

---

## Overview

This document inventories every product capability currently implemented in Jarvis V1, based on direct inspection of the Android codebase, backend services, Supabase schema, and existing documentation.

---

## Capability 01 — Signal Ingestion

| Field | Detail |
|-------|--------|
| **Capability Name** | Signal Ingestion |
| **Purpose** | Capture raw signals from SMS, WhatsApp, and email and store them for processing |
| **Current Status** | Working |
| **Dependencies** | Android app (JarvisCollector), Supabase Storage, ConsumerService |
| **User Value** | Foundation of everything — without reliable ingestion, no downstream intelligence is possible |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Partial — file-based upload mechanism should be replaced with real-time API push |

### Detail

The Android app captures:
- SMS via `Telephony.Sms.Inbox.CONTENT_URI` — reads all inbox messages
- WhatsApp notifications via `NotificationListenerService` — captures incoming notification text from `com.whatsapp` and `com.whatsapp.w4b`

Signals are serialised as JSON and uploaded to the Supabase Storage bucket (`jarvis-signals/incoming/`). The backend `ConsumerService` polls the bucket, downloads JSON files, deduplicates using SHA-256 file hashing, writes raw records to the `mobile_signals` SQLite table, and archives processed files.

**What works:** Ingestion is stable and reliable. Deduplication prevents double-processing.

**What does not work:** No real-time delivery — signals wait in Supabase Storage until the next backend poll cycle. Voice capture is entirely absent.

---

## Capability 02 — Signal Qualification

| Field | Detail |
|-------|--------|
| **Capability Name** | Signal Qualification |
| **Purpose** | Filter raw signals into QUALIFIED, REVIEW, or REJECTED before any LLM processing |
| **Current Status** | Working |
| **Dependencies** | `SignalQualificationAgent`, `config/family_context.json`, `config/high_value_domains.json`, `config/qualification_rules.json` |
| **User Value** | Prevents noise from reaching the expensive LLM pipeline; preserves financial signals |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Minor — add UI for the REVIEW queue |

### Qualification Logic

Filters applied in order:
1. Age filter: signals older than 90 days are rejected (`STALE_SIGNAL`)
2. Exact duplicate check within 48 hours (`DUPLICATE_SIGNAL`)
3. OTP keyword rejection
4. WhatsApp system noise rejection (call logs, media notifications)
5. Telecom data alerts rejection
6. Promotional keyword rejection (if not financial)
7. Group/community messages → REVIEW
8. Rules Engine ignore match

Boosts:
- Family context boost (+30): messages mentioning spouse/children name
- High-value domain boost (+30): medical, legal, financial, travel keywords

Financial preservation override: if a signal would be REJECTED but contains financial keywords, it is upgraded to REVIEW (score 25) instead.

Thresholds: score ≤ 20 → REJECTED, 21–59 → REVIEW, ≥ 60 → QUALIFIED.

---

## Capability 03 — Signal Understanding

| Field | Detail |
|-------|--------|
| **Capability Name** | Signal Understanding |
| **Purpose** | Transform qualified signals into canonical structured contracts consumed by downstream agents |
| **Current Status** | Working |
| **Dependencies** | `SignalUnderstandingAgent`, `IntelligenceRouter`, Ollama (local LLM: qwen3:1.7b) |
| **User Value** | Converts unstructured SMS text into typed, structured data that agents can act on |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Minor — expand deterministic rules for new signal formats |

### Contract Output

Every signal produces a canonical JSON contract containing:
- `classes`: FINANCIAL, INFORMATION, ACTION, ALERT, MEMORY
- `entities`: amount, merchant, deadline, people, organizations
- `confidence`: business confidence score (0.0–1.0)
- `routes`: list of downstream agents to receive the contract
- `processing_path`: RULE_ENGINE or LLM

The deterministic path handles 60–80% of signals. LLM handles the remainder.

---

## Capability 04 — Financial Transaction Processing

| Field | Detail |
|-------|--------|
| **Capability Name** | Financial Transaction Processing |
| **Purpose** | Process confirmed monetary events into typed FinancialFact records |
| **Current Status** | Working |
| **Dependencies** | `FinancialAgent`, `FinancialClassifier`, `RulesEngine`, merchant registry, bank account registry |
| **User Value** | The core financial intelligence — what money moved, where, to whom, categorised |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | No — algorithms are validated and locked |

### What Is Processed

- Bank debit/credit SMS (HDFC, SBI, ICICI, Axis, Kotak)
- UPI payment confirmations
- Credit card payment SMS
- Insurance premium receipts
- Investment (SIP/mutual fund) deductions

### What Is Not Processed

- Wallet-to-merchant spend (GPay Lite, Paytm)
- Card-based purchases without real-time SMS (credit card actual purchases)
- Cash transactions

---

## Capability 05 — Financial Aggregation

| Field | Detail |
|-------|--------|
| **Capability Name** | Financial Aggregation |
| **Purpose** | Compute monthly rollups: accounting spend, lifestyle spend, income, net cashflow, category totals, MoM trends |
| **Current Status** | Working |
| **Dependencies** | `AggregationService`, `FinancialFact` records |
| **User Value** | Monthly summary view — how much was spent, in which categories, compared to last month |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | No — idempotent and mathematically sound |

### Spending Views

- **Accounting Spend**: all debits minus internal transfers
- **Lifestyle Spend**: Accounting Spend minus investments, insurance premiums, credit card payments
- **Net Cashflow**: Total Income minus Accounting Spend

---

## Capability 06 — Internal Transfer Detection

| Field | Detail |
|-------|--------|
| **Capability Name** | Internal Transfer Detection |
| **Purpose** | Identify when money moves between the user's own bank accounts and exclude both legs from spending calculations |
| **Current Status** | Working |
| **Dependencies** | `FinancialAgent`, bank account registry, transfer type windows |
| **User Value** | Prevents spending inflation from self-transfers (HDFC→SBI, etc.) |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | No |

### Algorithm

4-condition check: amount match within ₹1 rounding, both legs resolve to known bank accounts, transfer keyword present in message, time window matches transfer type (UPI: 10 min, IMPS: 30 min, NEFT: 4 hrs, RTGS: 2 hrs).

---

## Capability 07 — Salary Detection

| Field | Detail |
|-------|--------|
| **Capability Name** | Salary Detection |
| **Purpose** | Identify salary credits and separate them from other income types |
| **Current Status** | Working |
| **Dependencies** | `FinancialAgent`, salary keywords, salary_sources registry |
| **User Value** | Accurate income figure in monthly summary |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Minor — salary_sources registry starts empty, needs bootstrapping |

### 4-Tier Algorithm

1. Keyword match (salary, sal cr, payroll) → confidence 0.95
2. Salary source registry match (known employer + expected day + amount tolerance) → 0.90
3. Recurring credit pattern (same sender, same day, 3 of 4 months, ≤15% variance) → 0.80 candidate
4. Large unmatched credit (≥₹20,000) → 0.50 INCOME_UNCLASSIFIED

---

## Capability 08 — Merchant Classification

| Field | Detail |
|-------|--------|
| **Capability Name** | Merchant Classification |
| **Purpose** | Categorise transactions by merchant (Zomato → FOOD_DINING, Zerodha → INVESTMENT, etc.) |
| **Current Status** | Working |
| **Dependencies** | `FinancialClassifier`, `RulesEngine`, `IntelligenceRouter` (LLM fallback) |
| **User Value** | Makes spending categories meaningful and actionable |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Minor — extend seed list, improve NACH/SIP detection |

### Resolution Order

1. Pre-seeded registry (24 merchants, 45+ aliases) → confidence 1.0
2. Heuristic keyword checks (fish, mutton, vegetables) → 1.0
3. Rules Engine (user overrides + dynamic merchant map) → 1.0
4. LLM classification (cached by SHA-256) → 0.9

---

## Capability 09 — Todo Management

| Field | Detail |
|-------|--------|
| **Capability Name** | Todo Management |
| **Purpose** | Create, prioritise, and deliver actionable task items from signals |
| **Current Status** | Working |
| **Dependencies** | `TodoAgent`, `todo_items` (SQLite), `todos` (Supabase), Android UI |
| **User Value** | Bill reminders, school events, medical appointments — captured automatically |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — add auto-completion detection, snooze, spouse visibility |

### What Creates Todos

- Bill due alerts (credit card, utility bills, EMI)
- Insurance renewal reminders
- Medical appointments
- School fee reminders, parent meetings
- Document renewal deadlines

### What Is Missing

- No snooze/deferral
- No auto-completion (payment SMS does not close the related todo)
- No spouse-shared todos

---

## Capability 10 — FYI Management

| Field | Detail |
|-------|--------|
| **Capability Name** | FYI Management |
| **Purpose** | Record informational events that require awareness but not action |
| **Current Status** | Working |
| **Dependencies** | `FyiAgent`, `fyi_events` (SQLite + Supabase), Android UI |
| **User Value** | Delivery updates, travel confirmations, school circulars — captured and accessible |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — add grouping to prevent FYI flood for the same delivery |

### FYI Categories

Delivery updates, travel bookings, school circulars, family updates, general informational content.

### What Is Missing

- No grouping (same delivery generates multiple FYI events)
- No linkage between related FYIs and Todos

---

## Capability 11 — Fact Memory

| Field | Detail |
|-------|--------|
| **Capability Name** | Fact Memory |
| **Purpose** | Store long-lived personal facts — employers, insurance policies, subscriptions, family details |
| **Current Status** | Working |
| **Dependencies** | `FactAgent`, `facts` table, `fact_relationships` table |
| **User Value** | Personal knowledge base — Jarvis remembers things the user tells it implicitly |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — add UI for viewing and editing facts |

### Fact Types

PERSON, SPOUSE, CHILD, BANK_ACCOUNT, INSURANCE_POLICY, VEHICLE, PROPERTY, SUBSCRIPTION, PREFERENCE, CONTACT.

---

## Capability 12 — Daily Brief Generation

| Field | Detail |
|-------|--------|
| **Capability Name** | Daily Brief Generation |
| **Purpose** | Synthesise all daily intelligence into a structured summary for the user |
| **Current Status** | Broken |
| **Dependencies** | `DailyBriefAgent`, `DailyBriefBuilder`, `daily_briefs` table, Android UI |
| **User Value** | The highest-value output of the entire system — a morning summary that eliminates the need to check multiple apps |
| **Preserve?** | Yes — architecture is correct |
| **Discard?** | Legacy generator only — discard `daily_brief_generator.py` |
| **Revisit?** | Yes — end-to-end fix required |

### What Is Broken

1. Legacy `daily_brief_generator.py` crashes on execution (model attribute mismatch)
2. Android app assembles briefs from local templates instead of consuming server brief
3. No API endpoint for Android to fetch the brief
4. Scheduler registers the brief job but doesn't run it reliably

### What Is Working

The `DailyBriefAgent` (in `src/agents/daily_brief/`) produces structured Morning and Evening briefs using the correct schema. The output is written to `daily_briefs` (Supabase). The problem is delivery to the user.

---

## Capability 13 — Streamlit Web Dashboard

| Field | Detail |
|-------|--------|
| **Capability Name** | Streamlit Web Dashboard |
| **Purpose** | Web interface for the owner to view financial summaries, trends, todos, FYIs, signals, diagnostics |
| **Current Status** | Working (owner use only) |
| **Dependencies** | Streamlit, Supabase |
| **User Value** | Low for typical daily use; high for debugging and inspection |
| **Preserve?** | Partially — as a debugging tool |
| **Discard?** | Not entirely, but should not be the primary user interface |
| **Revisit?** | Yes — simplify to a single monitoring page |

---

## Capability 14 — School Events

| Field | Detail |
|-------|--------|
| **Capability Name** | School Events |
| **Purpose** | Capture and surface school-related notifications (circulars, fee reminders, parent meetings) |
| **Current Status** | Partial — captured as FYIs and Todos but no structured school view |
| **Dependencies** | WhatsApp notification capture, FyiAgent, TodoAgent |
| **User Value** | High — missed school events cause family friction |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — needs dedicated structure, not generic FYI bucket |

---

## Capability 15 — Health Alerts

| Field | Detail |
|-------|--------|
| **Capability Name** | Health Alerts |
| **Purpose** | Capture medical appointments, pharmacy orders, health reminders |
| **Current Status** | Partial — appointments become Todos via the ACTION class; pharmacy orders become FYIs |
| **Dependencies** | SUA (medical appointment rule), FyiAgent, TodoAgent |
| **User Value** | Medium — captured but not presented distinctively |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — give health a clearer presentation slot in the brief |

---

## Capability 16 — Notification Delivery (Android Push)

| Field | Detail |
|-------|--------|
| **Capability Name** | Notification Delivery |
| **Purpose** | Push local system notifications for due todos |
| **Current Status** | Working for Todos only |
| **Dependencies** | `TodoNotificationWorker`, `TodoNotificationHelper` |
| **User Value** | Medium — alerts user to tasks due today or tomorrow |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — extend to push the Daily Brief as a notification |

---

## Capability 17 — User Profile / Context

| Field | Detail |
|-------|--------|
| **Capability Name** | User Profile / Context |
| **Purpose** | Maintain family context (names, priorities, ignore topics) for signal qualification |
| **Current Status** | Working — stored in `config/user_context.json` and `config/family_context.json` |
| **Dependencies** | Family context JSON, high-value domains JSON, qualification rules JSON |
| **User Value** | Enables family-aware signal qualification — spouse's name triggers family boost |
| **Preserve?** | Yes |
| **Discard?** | No |
| **Revisit?** | Yes — should be stored in database, not JSON files, to allow runtime editing |

---

## Capability 18 — Voice Capture

| Field | Detail |
|-------|--------|
| **Capability Name** | Voice Capture |
| **Purpose** | Allow user to capture a thought, reminder, or todo via voice input |
| **Current Status** | NOT IMPLEMENTED |
| **Dependencies** | N/A |
| **User Value** | Critical — this is the most important missing capability |
| **Preserve?** | N/A — does not exist |
| **Discard?** | N/A |
| **Revisit?** | Must be built for V2 |

---

## Capability Summary Matrix

| # | Capability | Status | Preserve | Discard | Revisit |
|---|-----------|--------|----------|---------|---------|
| 01 | Signal Ingestion | Working | Yes | No | Partial |
| 02 | Signal Qualification | Working | Yes | No | Minor |
| 03 | Signal Understanding | Working | Yes | No | Minor |
| 04 | Financial Processing | Working | Yes | No | No |
| 05 | Financial Aggregation | Working | Yes | No | No |
| 06 | Internal Transfer Detection | Working | Yes | No | No |
| 07 | Salary Detection | Working | Yes | No | Minor |
| 08 | Merchant Classification | Working | Yes | No | Minor |
| 09 | Todo Management | Working | Yes | No | Yes |
| 10 | FYI Management | Working | Yes | No | Yes |
| 11 | Fact Memory | Working | Yes | No | Yes |
| 12 | Daily Brief | Broken | Yes | Legacy only | Yes — urgent |
| 13 | Streamlit Dashboard | Working | Partial | Primary UI | Yes |
| 14 | School Events | Partial | Yes | No | Yes |
| 15 | Health Alerts | Partial | Yes | No | Yes |
| 16 | Notification Delivery | Working | Yes | No | Yes |
| 17 | User Profile / Context | Working | Yes | No | Yes |
| 18 | Voice Capture | Missing | N/A | N/A | Must Build |

---

*Document: 01_PRODUCT_CAPABILITIES.md*  
*Part of Jarvis V1 Migration Knowledge Base*
