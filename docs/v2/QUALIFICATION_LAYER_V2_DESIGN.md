# Qualification Layer V2 Design Document — Lineage & Metadata Preservation

Document Version: 2.0.0  
Date: 2026-07-11T11:06:50Z  
Status: **PROPOSED**  

---

## 1. Architectural Scope & Current-State Gaps

The current qualification pipeline introduces critical information loss at the `mobile_signals` → `qualified_signals` boundary:
* **Discarded Metadata:** Rich structured fields parsed by Phase 1B collectors (GPay and bank statement parameters) are dropped.
* **Lost Origin Context:** The `device_id` (identifying which device/user generated the signal) is discarded.
* **Broken Lineage:** The `message_hash` (the unique identifier for signal content) is discarded, preventing upstream tracking and deduplication replay.
* **Text-Only Guessing:** Downstream agents (SUA, Financial Agent) are forced to run expensive LLM requests to reconstruct structural fields (like amounts and merchants) that were already extracted during ingestion.

### Logical Dataflow (Current vs. Proposed)

```text
CURRENT STATE:
[mobile_signals] (device_id, message_hash, metadata)
       ↓
[Qualification Agent] (Scoring based on raw message text only)
       ↓
[qualified_signals] (Only signal_id, text, score/status; metadata and device_id are lost)


PROPOSED STATE:
[mobile_signals] (device_id, message_hash, metadata)
       ↓
[Qualification Agent] (Source-aware: uses metadata first, fallback to text scoring)
       ↓
[qualified_signals] (Preserves device_id, message_hash, and metadata; full lineage intact)
```

---

## 2. Proposed qualified_signals Schema Changes

To support lineage and metadata preservation, the `qualified_signals` table must be altered to include three new columns.

### Target Schema Definition
* `device_id` (`text`): Preserves the source device name (e.g. `shobana`, `pradeep`).
* `message_hash` (`text`): Mapped directly from `mobile_signals.message_hash` and enforced as `UNIQUE` to prevent duplicate qualification events.
* `metadata` (`jsonb`): Holds the complete structured JSON payload from the ingestion stage.

The DDL for these changes is located in [QUALIFICATION_SCHEMA_CHANGES.sql](file:///home/prad/petprojects/ai/jarvis/QUALIFICATION_SCHEMA_CHANGES.sql).

---

## 3. Source-Aware Qualification Strategy

Under V2, the qualification logic will become source-aware. Instead of applying text scoring universally, qualification is branched based on the signal source.

### 3.1 GPay Signals (Structured)
* **Strategy**: Metadata-First.
* **Logic**:
  - If `metadata` contains `amount`, `transaction_type`, and `counterparty`, the record is automatically qualified (`QUALIFIED` status, score `100.0`, reason `gpay_structured_metadata`).
  - If the transaction is flagged as a duplicate via `message_hash`, it is rejected.
  - If `metadata` is empty or incomplete, it falls back to the scoring-based logic.

### 3.2 Bank Statement Signals (Structured)
* **Strategy**: Metadata-First.
* **Logic**:
  - If `metadata` has valid transaction fields, it is classified as `QUALIFIED` (score `100.0`, reason `bank_statement_structured_metadata`).
  - This avoids running text-based keyword matchers on bank statements that contain noise (e.g., promotional terms mixed with balance details).

### 3.3 SMS / WhatsApp Signals (Unstructured)
* **Strategy**: Rule-Based Scoring Engine (Preserved from V1).
* **Logic**:
  - Applies age check (>90 days) -> `REJECTED`.
  - Applies pre-July WhatsApp filter -> `REJECTED`.
  - Filters out OTPs, system notifications, and promo keywords.
  - Computes contextual boosts (family names, high-value domains).
  - Financial preservation override: Promos or low-scoring messages containing financial keywords are preserved as `REVIEW` (score `25.0`).

---

## 4. Metadata Utilization Review

Below is the mapping and utility assessment of the parsed ingestion fields:

| Metadata Field | Current Usage | Proposed Usage | Qualification Impact | Downstream Impact |
|---|---|---|---|---|
| `amount` | Discarded | Preserved in `qualified_signals.metadata` | Qualifies structured signals immediately. | Plugs into SUA contract directly without LLM extraction. |
| `currency` | Discarded | Preserved in `qualified_signals.metadata` | None. | Direct mapping to contract. |
| `counterparty` | Discarded | Preserved in `qualified_signals.metadata` | Used for validation. | Maps to contract merchant directly. |
| `transaction_type`| Discarded | Preserved in `qualified_signals.metadata` | Direct eligibility check. | Maps to transaction type (DEBIT/CREDIT). |
| `reference_number`| Discarded | Preserved in `qualified_signals.metadata` | None. | Maps to transaction ID for deduplication. |
| `source_file_name`| Discarded | Preserved in `qualified_signals.metadata` | None. | Preserves source lineage. |
| `source_file_hash`| Discarded | Preserved in `qualified_signals.metadata` | None. | Used for file-level replay audits. |

---

## 5. Lineage Strategy

Lineage is preserved by carrying over the `message_hash` and `device_id` across the pipeline boundaries:
1. `mobile_signals.message_hash` $\rightarrow$ `qualified_signals.message_hash` $\rightarrow$ `understood_signals.contract_json.message_hash`.
2. Any downstream replay request targeting a signal can fetch the original raw signal from `mobile_signals` using the `message_hash` or the foreign key `signal_id`.
3. Idempotency is enforced by the unique constraint on `qualified_signals.message_hash`. Any attempt to double-qualify a record will trigger a database conflict and be safely ignored.
