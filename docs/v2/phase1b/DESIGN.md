# Phase 1B Design Document — Source Collectors

This document describes the design specifications, normalization mappings, and processing workflows implemented for the Jarvis V2 Source Collectors.

---

## 1. Collector Operations Scope

Phase 1B implements four specialized source collectors:
1. **WhatsApp Collector:** Polling `incoming/whatsapp/` (JSON exports).
2. **SMS Collector:** Polling `incoming/sms/` (JSON exports).
3. **GPay Collector:** Polling `incoming/gpay/` (PDF statement exports).
4. **Bank Statement Collector:** Polling `incoming/statements/` (SBI and HDFC PDF statements).

The collectors are scoped strictly to ingestion, normalization, and archiving. Downstream qualification, LLM processing, intent classification, and database computations are strictly omitted.

---

## 2. Ingestion Lifecycles

Each collector manages its own lifecycle for each discovered file:

```text
               Discover files in subdirectory
                             ↓
                 For each discovered file:
                             ↓
              Calculate hash & check duplicate
                             ↓
              Parse file bytes (JSON or PDF text)
                             ↓
                 For each record extracted:
               - Normalize to Unified Schema
               - Persist in mobile_signals
                             ↓
                   Archive processed file
                             ↓
                 Emit audit trail events
```

---

## 3. Signal Normalization Mapping

### WhatsApp Signal Mapping
* **Input Structure:**
  ```json
  {"sender": "Sender", "message": "Content text", "timestamp": 1782210550848, "attachment_indicator": false}
  ```
* **Normalized Target:**
  * `source_type`: `whatsapp`
  * `source_subtype`: `chat`
  * `sender`: msg["sender"]
  * `receiver`: "user_alias" (default)
  * `content`: msg["message"]
  * `source_event_time`: UTC conversion of `timestamp`
  * `metadata`: `{"chat_name": "...", "attachment_indicator": ...}`

### SMS Signal Mapping
* **Input Structure:**
  ```json
  {"sender": "Sender ID", "message": "Content text", "timestamp": 1782209436034}
  ```
* **Normalized Target:**
  * `source_type`: `sms`
  * `source_subtype`: `inbox`
  * `sender`: msg["sender"]
  * `receiver`: "user_alias" (default)
  * `content`: msg["message"]
  * `source_event_time`: UTC conversion of `timestamp`
  * `metadata`: `{}`

### GPay & Bank Statement Financial Mapping
* **Input Structure:** Alphanumeric/regex matches from PDF pages.
* **Normalized Target:**
  * `source_type`: `financial`
  * `source_subtype`: `gpay` or `bank_statement`
  * `content`: tx["description"]
  * `sender`: if CREDIT: `counterparty`, if DEBIT: `user_alias`
  * `receiver`: if CREDIT: `user_alias`, if DEBIT: `counterparty`
  * `source_event_time`: Parse date/time strings to UTC ISO format.
  * `metadata`: **Financial Transaction Schema**:
    ```json
    {
      "transaction_date": "...",
      "amount": 1500.0,
      "currency": "INR",
      "transaction_type": "DEBIT|CREDIT",
      "description": "...",
      "reference_number": "...",
      "counterparty": "..."
    }
    ```
