# Signal Taxonomy: Jarvis Canonical Signal Model

This document defines the canonical taxonomy, routing rules, and entity extraction contract that acts as the communication interface for all Jarvis Agents.

---

## 1. Real Signal Samples

### WhatsApp
* *"Did you bring the grocery items?"* (Source: WhatsApp | Category: Personal | Type: Task/Action)
* *"Circular: Science project model submission due by Wednesday"* (Source: WhatsApp | Category: Education | Type: Task + Info)

### SMS
* *"ALERT: UPI transaction of INR 1500.00 spent on Zomato from HDFC card ending 1234. Ref: 67890"* (Source: SMS | Category: Finance | Type: Financial)
* *"Your one-time verification password code is 887755. Use within 10 minutes."* (Source: SMS | Category: Security | Type: OTP/Noise)

### Email
* *"Your Amazon package was delivered."* (Source: Email | Category: Shopping | Type: Information)
* *"Electricity bill for A/C 998811 of INR 4500 is due on 2026-07-01"* (Source: Email | Category: Finance | Type: Financial + Action)

---

## 2. Primary Signal Classes

Every ingested signal must map to one or more of the following primary classes:

* **ACTION**: Actionable tasks or direct requests requiring user intervention (e.g. chores, homework submissions, bills to pay).
* **FINANCIAL**: Monetary transactions, expenses, receipts, credit/debit alerts, or payment invoices.
* **INFORMATION**: FYI circulars, delivery tracking updates, newsletters, or informational reports.
* **MEMORY**: Semantic facts, preferences, dates of historical interest, or profile updates to be stored in the knowledge base.
* **ALERT**: High-urgency security notices, system failures, transaction disputes, or account locks.
* **NOISE**: One-Time Passwords (OTPs), verification codes, advertising promos, or automated device state notifications.

---

## 3. Multi-Class Composition Rules

Signals can belong to **multiple classes** simultaneously. 

### Composition Scenarios
* *School Circular with Homework*:
  `INFORMATION` (circular context) + `ACTION` (homework submission task) + `MEMORY` (due date/exam date registration).
* *Utility Invoice Email*:
  `FINANCIAL` (bill amount) + `ACTION` (payment task) + `INFORMATION` (billing statement).

### Composition Rules
1. **Dominant Class**: The Signal Understanding Agent determines the primary class for initial routing.
2. **Decomposition**: If a signal belongs to multiple classes, the primary agent spawns child records or triggers sub-agents (e.g., a Financial Agent processing a bill triggers the Todo Agent to set a payment reminder).

---

## 4. Signal Importance

Importance defines how and when the user is notified:

* **CRITICAL**: Immediate attention needed. Security breaches, card block alerts, suspicious transaction warnings.
* **HIGH**: Family direct chats, parenting tasks, school circular announcements, bills due within 48 hours.
* **MEDIUM**: Standard shipping deliveries, work notifications, bills due in > 3 days.
* **LOW**: Non-urgent personal interests, transaction receipts, routine general summaries.
* **IGNORE**: System health checks, OTP verification codes (discarded after ingestion).

---

## 5. Agent Routing Matrix

Signals are routed to specialist agents based on their classification:

```text
               Ingested Signal
                      │
                      ▼
            Signal Intake Agent
                      │
                      ▼ (candidate_signals)
           Signal Understanding Agent
                      │
    ┌─────────────────┼─────────────────┬─────────────────┐
    ▼                 ▼                 ▼                 ▼
  [ACTION]       [FINANCIAL]      [INFORMATION]       [MEMORY]
    │                 │                 │                 │
    ▼                 ▼                 ▼                 ▼
Todo Agent     Financial Agent      FYI Agent        Fact Agent
```

---

## 6. Entity Extraction Schema

The Signal Understanding Agent extracts a strict list of entities:

* **People**: Direct names of individuals (e.g. `'Shobana'`, `'Teacher'`).
* **Organizations**: Banks, schools, and companies (e.g. `'HDFCBank'`, `'Oakridge School'`).
* **Merchants**: Transaction payees (e.g. `'Zomato'`, `'Amazon'`).
* **Money**: Structured currency code and float amount (e.g. `{"amount": 1500.00, "currency": "INR"}`).
* **Dates & Deadlines**: Parsed target dates in ISO format (`YYYY-MM-DD`).

---

## 7. Canonical Signal Understanding Output Contract

This JSON structure is the exact contract emitted by the Signal Understanding Agent. No downstream agent is required to parse raw message text.

```json
{
  "signal_type": "school_update | financial_transaction | delivery_update | general",
  "classes": ["ACTION", "INFORMATION", "MEMORY"],
  "importance": "CRITICAL | HIGH | MEDIUM | LOW | IGNORE",
  "summary": "Short synthetic summary of message",
  "confidence": 0.95,
  "reason": "Derived from keyword 'due date' and sender 'Oakridge School'",
  "entities": {
    "people": ["name"],
    "organizations": ["org_name"],
    "merchants": ["merchant_name"],
    "monetary_value": {
      "amount": 120.00,
      "currency": "USD"
    },
    "deadlines": ["2026-06-25"]
  },
  "routes": ["TodoAgent", "FyiAgent"],
  "raw_context": {
    "source": "whatsapp | sms | email",
    "sender": "Original Sender String",
    "timestamp": "2026-06-23T14:09:00Z"
  }
}
```
Using this schema, downstream agents process only clean, normalized properties, shielding them from raw-source variations.
