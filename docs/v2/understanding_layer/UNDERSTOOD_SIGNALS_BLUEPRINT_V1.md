# UNDERSTOOD SIGNALS BLUEPRINT V1

Document Version: 1.0.0  
Date: 2026-07-11T11:44:34Z  
Status: **DESIGN REVIEW ONLY (NO CODE / NO EXECUTION)**  

---

## 1. Purpose & Core Problem Solved

The `understood_signals` table represents the **semantic contract boundary** of the Jarvis V2 intelligence pipeline. 

### Why can't downstream systems read directly from `qualified_signals`?
1. **Lack of Structure**: `qualified_signals` contains raw message strings (e.g. WhatsApp chats, SMS notifications). Downstream systems (like the Todo Agent or Financial Ledger) cannot parse unstructured strings reliably.
2. **Heterogeneous Sources**: Signals come from diverse channels (PDF statement parser outputs, GPay collector logs, SMS alerts, WhatsApp group threads). Downstream systems shouldn't manage source-specific formats.
3. **No Semantic Type**: A qualified signal has a score and a status, but no semantic category (e.g. is it a task, a transaction, or a medical fact?).

### What problem does `understood_signals` solve?
It acts as a **unified normalization layer**. It converts raw signal data into typed, validated, and structured JSON contracts that represent a single, clear intention.

### What information is added by the understanding step?
* **Signal Type Classification**: Maps signals into one of five core categories (`FINANCIAL`, `ACTION`, `FYI`, `FACT`, `NOISE`).
* **Semantic Summary**: A clear, concise natural language sentence explaining the record.
* **Contract Schema (`contract_json`)**: Extraction of type-specific key-value attributes (e.g., amount, currency, task name, due dates).
* **Confidence Rating**: A score (`0.0` to `1.0`) indicating the extraction quality.
* **Processing Path**: Tracks whether the record was processed via the LLM path or via the deterministic metadata bypass.

### Strict 1:1 Lineage Mapping
The relationship between `qualified_signals` (specifically those marked `QUALIFIED`) and `understood_signals` is **strictly 1:1**.
* **Single Intent Assumption**: Each qualified signal represents a single ingested event. Even if a raw message contains compound user intents (e.g., *"I paid Radha Rs 1500, also please buy bread"*), the Signal Understanding Agent is constrained to classify it under a single dominant `signal_type` and generate exactly one contract row in `understood_signals`.
* **Database Enforceability**: To guarantee this invariant, a unique constraint is defined on `qualified_signal_id` in `understood_signals`, ensuring a single raw signal can never spawn duplicate or branching understanding records.

---

## 2. Input Contract

A single row from `qualified_signals` serves as the input.

### Column Mapping Requirements

| Column | Type | Requirement | Usage in Understanding Stage |
|---|---|---|---|
| `id` | `uuid` | **Required** | Becomes `qualified_signal_id` for downstream join lineage. |
| `signal_id` | `bigint` | **Required** | Becomes `raw_signal_id` to link directly to the source `mobile_signals`. |
| `source` | `text` | **Required** | Triggers source-specific handling (e.g., gpay bypass vs WhatsApp LLM prompt). |
| `sender` | `text` | **Required** | Provided to the LLM to understand context/identities. |
| `message` | `text` | **Required** | Primary source text for LLM parsing. |
| `timestamp` | `timestamptz` | **Required** | Used to resolve relative dates (e.g. "tomorrow", "next Friday"). |
| `device_id` | `text` | **Required** | Used to attribute which family member or device generated the task/event. |
| `message_hash` | `text` | **Required** | Carried over for idempotency. |
| `metadata` | `jsonb` | **Required** | Parsed directly for structured records (amount, currency, etc.). |
| `amount` | `numeric` | *Optional* | Physical column used as fallback/validation. |
| `currency` | `varchar` | *Optional* | Physical column used as fallback/validation. |
| `transaction_type` | `varchar` | *Optional* | Physical column used as fallback/validation. |

---

### Real Ingestion Examples

#### 1. GPay Ingested Signal
```json
{
  "source": "gpay",
  "sender": "pprad",
  "message": "Paid to Radha Radha",
  "device_id": "pradeep",
  "message_hash": "6f1de9d316d846...",
  "metadata": {
    "source_metadata": {
      "amount": 1536.0,
      "currency": "INR",
      "counterparty": "Radha Radha",
      "transaction_type": "DEBIT",
      "reference_number": "120940047278",
      "source_file_name": "gpay_statement.pdf"
    }
  }
}
```
* **Used**: `source_metadata` fields (`amount`, `currency`, `counterparty`, `transaction_type`, `reference_number`).
* **Ignored**: File path hashes, system upload metrics.

#### 2. Bank Statement Ingested Signal
```json
{
  "source": "bank_statement",
  "sender": "hdfc",
  "message": "ATM Cash Withdrawal HDFC",
  "device_id": "shobana",
  "message_hash": "7a3b4c5d...",
  "metadata": {
    "source_metadata": {
      "amount": 5000.0,
      "currency": "INR",
      "transaction_type": "DEBIT",
      "reference_number": "WDL99402910"
    }
  }
}
```
* **Used**: `amount`, `currency`, `transaction_type`, `reference_number`.

#### 3. SMS Ingested Signal
```json
{
  "source": "sms",
  "sender": "SBI-ALERT",
  "message": "Your a/c no. XXX1234 is debited for Rs 2500.00 on 2026-07-11...",
  "device_id": "pradeep",
  "message_hash": "a1b2c3d4...",
  "metadata": {}
}
```
* **Used**: The entire `message` string (for regex parser or LLM fallback extraction).

#### 4. WhatsApp Ingested Signal
```json
{
  "source": "whatsapp",
  "sender": "Shobana",
  "message": "Can you buy bread and milk on your way back home today?",
  "device_id": "shobana",
  "message_hash": "a9b8c7d6...",
  "metadata": {}
}
```
* **Used**: `message`, `timestamp`, `sender`, `device_id`.

---

## 3. Understanding Output Contract

When written to `understood_signals`, every record must contain a `contract_json` conforming to its classified type.

### 3.1 Financial Signal Contract
* **Usage**: Ingests into personal Ledger.
* **Fields**: `amount` (float), `currency` (string), `transaction_type` (DEBIT/CREDIT), `payment_channel` (UPI/CARD/CASH/UNKNOWN), `merchant` (string).
* **Sample Output**:
```json
{
  "amount": 1536.0,
  "currency": "INR",
  "transaction_type": "DEBIT",
  "payment_channel": "UPI",
  "merchant": "Radha Radha"
}
```

### 3.2 Action Signal Contract
* **Usage**: Feeds into the Task/Todo Agent.
* **Fields**: `task_name` (string), `due_date` (ISO timestamp string or null), `assigned_to` (string), `priority` (LOW/MEDIUM/HIGH).
* **Sample Output**:
```json
{
  "task_name": "Buy bread and milk on the way back home",
  "due_date": "2026-07-11T23:59:59Z",
  "assigned_to": "pradeep",
  "priority": "MEDIUM"
}
```

### 3.3 FYI Signal Contract
* **Usage**: Broadcasts family updates/logs.
* **Fields**: `summary` (string), `topic` (string), `event_date` (ISO timestamp string or null).
* **Sample Output**:
```json
{
  "summary": "Pradeep is heading to Chennai for a meeting",
  "topic": "travel",
  "event_date": "2026-07-11T12:00:00Z"
}
```

### 3.4 Fact Signal Contract
* **Usage**: Updates the long-term semantic memory layer.
* **Fields**: `entity` (string), `attribute` (string), `value` (string), `summary` (string).
* **Sample Output**:
```json
{
  "entity": "Radha Radha",
  "attribute": "preferred payment method",
  "value": "GPay UPI",
  "summary": "Preferred payment method for Radha Radha is GPay UPI."
}
```

### 3.5 Noise Signal Contract
* **Usage**: Ignored downstream but logged for validation auditing.
* **Fields**: `reason` (string).
* **Sample Output**:
```json
{
  "reason": "telecom data alerts or OTP confirmation"
}
```

---

## 4. Classification Framework

The pipeline categorizes signals into five distinct buckets:

```text
                  Incoming Signal (qualified_signals)
                                  │
      ┌───────────────────────────┼───────────────────────────┐
      ▼                           ▼                           ▼
[ FINANCIAL ]                 [ ACTION ]                   [ FYI ]
- Transaction details        - Action items / Tasks       - Informational alerts
- debits, credits, UPI       - due dates, assignments     - status updates
      │                           │                           │
      └───────────────────────────┼───────────────────────────┘
                                  ▼
                             [ FACT ] ──► Permanent knowledge updates
                                  ▼
                             [ NOISE ] ──► System warnings / OTP / Duplicates
```

| Category | Definition | Qualification Criteria | Example Input | Example Output |
|---|---|---|---|---|
| **FINANCIAL** | Any event showing money debited, credited, or a billing charge. | Contains transactional value, currency, and counterparty. | `Paid to Radha Radha Rs. 1536` | Ledger contract containing amount, merchant, and channel. |
| **ACTION** | A command, request, or reminder indicating a task to be performed. | Has an action verb, implied actor, or explicit deadline. | `Can you pay the electric bill by tomorrow?` | Todo contract with task name and deadline. |
| **FYI** | Informative context that doesn't require direct action. | Informational update on status, location, or timing. | `Flight ticket booked for July 25th.` | Calendar/FYI contract with description and date. |
| **FACT** | Static knowledge or relational data. | Introduces permanent rules, preferences, or properties. | `Aravind's registration number is TN09CZ8201` | Memory key-value (Aravind -> reg_no -> TN09CZ8201). |
| **NOISE** | Promos, spam, or service confirmations. | Lacks actionability, financial details, or long-term value. | `You have used 50% of your daily internet limit.` | Log showing Noise category and reason. |

---

## 5. Where the LLM Plays a Role

The LLM (Local Ollama `qwen2.5:1.5b` model) acts as a **semantic translator**. The table below highlights where the LLM performs reasoning versus where the pipeline extracts data deterministically from metadata.

### Division of Labor

| Attribute | Derived by LLM | Extracted from Metadata | LLM Role / Reasoning |
|---|---|---|---|
| **`signal_type`** | **YES** *(for SMS/WhatsApp)* | **NO** *(for GPay/Statements)* | For unstructured SMS or chats, the LLM infers intent (e.g. distinguishing *"I'll pay Radha"* (Action) from *"Paid Radha"* (Financial)). |
| **`summary`** | **YES** | **NO** | Combines signal sender, context, and message body to write a clean natural language summary. |
| **`entities`** | **YES** | **NO** | Identifies names, banks, or shops using Named Entity Recognition (NER). |
| **`financial attributes`** | **YES** *(for SMS)* | **YES** *(for GPay/Statements)* | On unstructured SMS, the LLM parses numerical amounts and currencies from variable positions in text. |
| **`action items`** | **YES** | **NO** | Parses tasks and translates relative dates (e.g. "tomorrow") into absolute UTC dates. |
| **`confidence`** | **YES** | **NO** | The LLM outputs a confidence rating reflecting its extraction certainty. |

---

## 6. Structured Signal Handling (GPay & Bank Statements)

For structured inputs, we completely bypass the LLM to eliminate processing latency, prevent timeouts, and avoid hallucination errors.

```text
Structured Signal (GPay/Statement)
               │
               ▼
   [ Metadata Bypass Logic ] ──► Extract: amount, currency, counterparty, tx_type
               │
               ▼
   [ Generate Local Summary ] ──► "Paid to [Merchant] [Amount]"
               │
               ▼
[ Insert to understood_signals ] (No LLM call executed!)
```

### Deterministic Extraction Fields (100% Code-Based)
* `amount`: Parsed directly from `metadata.source_metadata.amount`
* `currency`: Mapped from `metadata.source_metadata.currency`
* `merchant`: Mapped from `metadata.source_metadata.counterparty`
* `transaction_type`: Mapped from `metadata.source_metadata.transaction_type`

### LLM Call Requirement
* **LLM Call Required**: **NO**.
* By bypassing the LLM, these records are processed in milliseconds instead of hitting the 30-second Ollama timeout penalty on CPU.

---

## 7. Unstructured Signal Handling (SMS & WhatsApp)

Because SMS and WhatsApp messages lack pre-parsed structures, they require the LLM.

### 7.1 Prompting Strategy
We use a **Strict JSON Schema Prompt**. The LLM is instructed:
1. You are the Jarvis Semantic Parser.
2. Analyze the following message: `[Message Text]` sent by `[Sender]` on `[Timestamp]`.
3. Reference the current date and time: `[Current Time]` to resolve relative dates.
4. Output a single JSON block matching the target contract schema. Do not output conversational text.

### 7.2 Classification Strategy
The LLM is prompted with the five categories and must return exactly one inside the `signal_type` JSON key.

### 7.3 Extraction Strategy
The prompt contains type-specific fields. The LLM extracts the variables, normalizes currencies to standard formats, and maps relative deadlines to absolute timestamps.

---

## 8. Proposed Schema for understood_signals

Below is the DDL for the `understood_signals` table in Supabase. It uses a foreign key constraint linking directly back to the V2 `qualified_signals` table.

```sql
-- ============================================================================
-- DDL FOR UNDERSTOOD SIGNALS
-- Schema: jarvis_insights_schemav1
-- Table: understood_signals
-- ============================================================================

CREATE TABLE jarvis_insights_schemav1.understood_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Lineage Links
    qualified_signal_id UUID NOT NULL UNIQUE REFERENCES jarvis_insights_schemav1.qualified_signals(id) ON DELETE CASCADE,
    raw_signal_id BIGINT NOT NULL, -- Lineage to mobile_signals.id
    device_id TEXT NOT NULL,       -- Preserves the originating device context
    message_hash TEXT NOT NULL UNIQUE, -- Enforces contract level idempotency
    metadata JSONB NOT NULL,       -- Carries the canonical metadata payload
    
    -- Classification
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('FINANCIAL', 'ACTION', 'FYI', 'FACT', 'NOISE')),
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 1.00 CHECK (confidence >= 0.00 AND confidence <= 1.00),
    
    -- Normalized Contract Output
    summary TEXT NOT NULL,
    contract_json JSONB NOT NULL,
    
    -- Metadata Auditing
    processing_path VARCHAR(20) NOT NULL CHECK (processing_path IN ('llm', 'metadata_bypass', 'fallback')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexing for performance
CREATE INDEX idx_understood_signals_type ON jarvis_insights_schemav1.understood_signals(signal_type);
CREATE INDEX idx_understood_signals_qualified_id ON jarvis_insights_schemav1.understood_signals(qualified_signal_id);
```

---

## 9. Validation Strategy

To ensure absolute safety and accuracy before re-enabling downstream execution, the following validation framework is proposed:

1. **No Signal Loss Check**:
   - **Assertion**: Count of `understood_signals` must match the count of `qualified_signals` with status `QUALIFIED`.
   - **Query**:
     ```sql
     SELECT COUNT(*) FROM jarvis_insights_schemav1.qualified_signals WHERE qualification_status = 'QUALIFIED';
     -- Must match:
     SELECT COUNT(*) FROM jarvis_insights_schemav1.understood_signals;
     ```
2. **No Lineage Loss Check**:
   - **Assertion**: Every row in `understood_signals` must have matching values for `device_id` and `message_hash` traced back to `mobile_signals`.
   - **Query**:
     ```sql
     SELECT COUNT(*) FROM jarvis_insights_schemav1.understood_signals us
     JOIN jarvis_insights_schemav1.qualified_signals qs ON us.qualified_signal_id = qs.id
     JOIN jarvis_insights_schemav1.mobile_signals ms ON qs.signal_id = ms.id
     WHERE qs.message_hash IS DISTINCT FROM ms.message_hash;
     ```
3. **Deterministic Replay Check**:
   - Re-running the backfill on the same `mobile_signals` dataset must result in identical UUIDs (or identical contract properties) in `understood_signals`, protecting idempotency.
4. **Classification Accuracy Check**:
   - A manual audit check of 50 randomly sampled contracts in `understood_signals` to verify if the LLM-derived `signal_type` matches human evaluation.
