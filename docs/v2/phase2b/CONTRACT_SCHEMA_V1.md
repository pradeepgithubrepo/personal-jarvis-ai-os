# CONTRACT_SCHEMA_V1.md — Canonical Signal Contract Specification

> Jarvis V2 · Phase 2B  
> Version: 1  
> Produced: 2026-07-10

---

## Purpose

This document defines the versioned canonical contract that the Signal Understanding Agent (SUA) produces and that all downstream agents must consume. It is the authoritative interface specification between SUA and every downstream agent.

> **Build Constitution BC-5:** No downstream agent may receive the raw message string, re-parse the message for amounts/merchants/deadlines, or derive its own classification from raw text. The contract is the only interface.

---

## Ownership

| Role | Agent |
|------|-------|
| **Producer** | Signal Understanding Agent (SUA) |
| **Consumers** | Financial Agent, Todo Agent, FYI Agent, Fact Agent |

The SUA writes `contract_json` into the `understood_signals.contract_json` column. Downstream agents read this field exclusively. They never receive or inspect the raw `message` column.

---

## Versioning

```text
contract_version = 1
```

The `contract_version` field is always present in `contract_json`. When the contract schema changes, the version is incremented and a new CONTRACT_SCHEMA_V2.md is produced. Consumers must check the version field before processing. Unknown versions must be rejected.

---

## Top-Level Contract Structure

```json
{
  "contract_version": 1,

  "signal_type": "FINANCIAL",

  "importance": 0.91,

  "confidence": 0.88,

  "summary": "Debit of INR 5000 via UPI to Amazon",

  "entities": ["Amazon", "HDFC"],

  "memory_candidate": false,

  "requires_action": false,

  "financial_candidate": true,

  "fact_candidate": false,

  "fyi_candidate": false,

  "noise_candidate": false,

  "type_specific": {
    "amount": 5000.0,
    "currency": "INR",
    "transaction_type": "DEBIT",
    "payment_channel": "UPI",
    "merchant": "Amazon",
    "transaction_id": null,
    "event_date": "2026-07-10T04:00:00Z"
  }
}
```

---

## Field Specifications

### Core Fields (All Signal Types)

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `contract_version` | `integer` | ✅ | Must be `1` | Schema version. Reject if unknown. |
| `signal_type` | `string` | ✅ | Enum: `FINANCIAL`, `ACTION`, `FYI`, `FACT`, `NOISE` | The classification produced by SUA. |
| `importance` | `float` | ✅ | `[0.0, 1.0]` | Priority weight. Higher = more important. |
| `confidence` | `float` | ✅ | `[0.0, 1.0]` | SUA's confidence in the classification. |
| `summary` | `string` | ✅ | Non-empty, max 500 chars | Human-readable 1-sentence summary. |
| `entities` | `list[string]` | ✅ | May be empty `[]` | Extracted proper nouns from the message (names, brands, orgs). |
| `memory_candidate` | `boolean` | ✅ | — | True if this signal should be stored in long-term memory (facts). |
| `requires_action` | `boolean` | ✅ | — | True if this signal requires a human action (ACTION type). |
| `financial_candidate` | `boolean` | ✅ | — | True iff `signal_type == FINANCIAL`. |
| `fact_candidate` | `boolean` | ✅ | — | True iff `signal_type == FACT`. |
| `fyi_candidate` | `boolean` | ✅ | — | True iff `signal_type == FYI`. |
| `noise_candidate` | `boolean` | ✅ | — | True iff `signal_type == NOISE`. |
| `type_specific` | `object` | ❌ | May be `{}` or absent for NOISE | Type-specific payload. Schema depends on `signal_type`. |

### Candidate Flag Consistency Rules

The candidate flags are derived directly from `signal_type`. Exactly one of the `*_candidate` flags must be `true`. Validators enforce:

```
financial_candidate == (signal_type == "FINANCIAL")
fact_candidate      == (signal_type == "FACT")
fyi_candidate       == (signal_type == "FYI")
noise_candidate     == (signal_type == "NOISE")
requires_action     == (signal_type == "ACTION")
memory_candidate    == (signal_type in {"FACT", "ACTION", "FYI"})
```

---

## Type-Specific Contract Schemas

### FINANCIAL

Dispatched to: `financial_agent`, optionally `fact_agent` when `memory_candidate=True`

```json
{
  "amount": 5000.0,
  "currency": "INR",
  "transaction_type": "DEBIT",
  "payment_channel": "UPI",
  "merchant": "Amazon India",
  "transaction_id": "TXN123456789",
  "event_date": "2026-07-10T04:00:00Z"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `amount` | `float\|null` | ❌ | `>= 0` if present |
| `currency` | `string\|null` | ❌ | e.g. `"INR"`, `"USD"` |
| `transaction_type` | `string` | ✅ | Enum: `DEBIT`, `CREDIT`, `UNKNOWN` |
| `payment_channel` | `string` | ✅ | Enum: `UPI`, `CARD`, `NEFT`, `RTGS`, `IMPS`, `CASH`, `UNKNOWN` |
| `merchant` | `string\|null` | ❌ | Canonical merchant name |
| `transaction_id` | `string\|null` | ❌ | Bank/UPI transaction reference |
| `event_date` | `string\|null` | ❌ | ISO 8601 timestamp of transaction |

---

### ACTION

Dispatched to: `todo_agent`, optionally `fact_agent` when `memory_candidate=True`

```json
{
  "task_name": "Call plumber for kitchen tap repair",
  "assignee": "User",
  "due_date": null
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `task_name` | `string` | ✅ | Non-empty |
| `assignee` | `string` | ✅ | Default `"unknown"` if not determinable |
| `due_date` | `string\|null` | ❌ | ISO 8601 date string if present |

---

### FYI

Dispatched to: `fyi_agent`

```json
{
  "event_name": "Flight AI-101 departure",
  "event_time": "2026-07-12T08:30:00Z",
  "description": "Flight AI-101 Chennai to Delhi, gate 4B"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `event_name` | `string` | ✅ | Non-empty |
| `event_time` | `string\|null` | ❌ | ISO 8601 if present |
| `description` | `string\|null` | ❌ | Optional detailed text |

---

### FACT

Dispatched to: `fact_agent`

```json
{
  "entity": "User",
  "attribute": "employer",
  "value": "Accenture"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `entity` | `string` | ✅ | Non-empty subject of the fact |
| `attribute` | `string` | ✅ | Non-empty attribute/property name |
| `value` | `string` | ✅ | Non-empty fact value |

---

### NOISE

Dispatched to: `none` — pipeline terminates

```json
{}
```

No type-specific fields. `type_specific` is always empty for NOISE.

---

## Invalid Contract Handling

When a contract fails validation:

1. **Reject** — do not dispatch to any agent
2. **Log** — structured log with `signal_type`, `understood_signal_id`, list of validation errors
3. **Audit** — write a `signal_routes` record with `route_status = "VALIDATION_FAILED"`
4. **Never** silently pass an invalid contract downstream

---

## Full Example — FINANCIAL

```json
{
  "contract_version": 1,
  "signal_type": "FINANCIAL",
  "importance": 0.91,
  "confidence": 0.88,
  "summary": "Debit of INR 5000 via UPI to Amazon",
  "entities": ["Amazon", "HDFC"],
  "memory_candidate": false,
  "requires_action": false,
  "financial_candidate": true,
  "fact_candidate": false,
  "fyi_candidate": false,
  "noise_candidate": false,
  "type_specific": {
    "amount": 5000.0,
    "currency": "INR",
    "transaction_type": "DEBIT",
    "payment_channel": "UPI",
    "merchant": "Amazon India",
    "transaction_id": "TXN123456789",
    "event_date": "2026-07-10T04:00:00Z"
  }
}
```

## Full Example — NOISE

```json
{
  "contract_version": 1,
  "signal_type": "NOISE",
  "importance": 0.1,
  "confidence": 1.0,
  "summary": "Good morning message",
  "entities": [],
  "memory_candidate": false,
  "requires_action": false,
  "financial_candidate": false,
  "fact_candidate": false,
  "fyi_candidate": false,
  "noise_candidate": true,
  "type_specific": {}
}
```

---

*Document: CONTRACT_SCHEMA_V1.md*  
*Phase 2B — Routing Layer + Canonical Contract Governance*
