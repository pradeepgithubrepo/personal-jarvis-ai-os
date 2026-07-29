# Qualification Layer V2 Design Document

Document Version: 2.1.0  
Date: 2026-07-11T11:15:32Z  
Status: **PROPOSED**  

---

## 1. Architectural Scope & Current-State Gaps

The current qualification pipeline introduces critical information loss at the `mobile_signals` → `qualified_signals` boundary:
* **Discarded Metadata:** Rich structured fields parsed by Phase 1B collectors (GPay and bank statement parameters) are dropped.
* **Lost Origin Context:** The `device_id` is discarded.
* **Broken Lineage:** The `message_hash` is discarded, preventing upstream tracking and deduplication replay.
* **Text-Only Guessing:** Downstream agents (SUA, Financial Agent) are forced to run expensive LLM requests to reconstruct structural fields (like amounts and merchants) that were already extracted during ingestion.

---

## 2. Minimum Metadata Contracts for Automatic Qualification

To qualify a structured signal automatically without running text rejections or scoring, it must satisfy the minimum metadata contract:

### 2.1 GPay Metadata Contract
The `mobile_signals.metadata` must contain the following keys with valid types:
* `amount` (numeric float, positive)
* `currency` (string, 3 characters, e.g. `"INR"`)
* `counterparty` (string, non-empty)
* `transaction_type` (string, either `"DEBIT"` or `"CREDIT"`)

### 2.2 Bank Statement Metadata Contract
The `mobile_signals.metadata` must contain the following keys with valid types:
* `amount` (numeric float, positive)
* `currency` (string, 3 characters, e.g. `"INR"`)
* `transaction_type` (string, either `"DEBIT"` or `"CREDIT"`)
* `description` or `reference_number` (string, non-empty)

If any of these fields are missing or null in `metadata`, the record is not automatically qualified and falls back to scoring-based/review-based qualification.

---

## 3. Physical Column Promotion vs. JSON

We propose promoting common financial fields to **physical columns** in `qualified_signals` alongside the JSON metadata block:
* `amount` (`numeric(12, 2)`)
* `currency` (`varchar(3)`)
* `transaction_type` (`varchar(10)`)

### Rationale
1. **Indexability & Performance:** Querying and indexing transaction aggregates (e.g. total spend for a date range) is significantly faster and cheaper on physical columns than inside jsonb documents.
2. **Database Constraints:** Enables database-level check constraints (e.g. `CONSTRAINT check_tx_type CHECK (transaction_type IN ('DEBIT', 'CREDIT'))`).
3. **Downstream Simplicity:** Downstream agents can directly read from physical columns, ensuring a strict, typed contract.

---

## 4. Canonical Payload Design (`payload_json`)

The `qualified_signals.metadata` will store a canonical JSON block designed to survive all future pipeline stages without information loss:

```json
{
  "canonical_version": 1,
  "source_metadata": {
    "amount": 1234.56,
    "currency": "INR",
    "transaction_type": "DEBIT",
    "payment_channel": "UPI",
    "counterparty": "SAMPLE HOTEL",
    "reference_number": "TXN202607110992",
    "source_file_name": "sample_gpay_statement.pdf",
    "source_file_hash": "a1b2c3d4e5f6g7h8i9j0a1b2c3d4e5f6g7h8i9j0a1b2c3d4e5f6g7h8i9j0a1b2",
    "source_ingested_at": "2026-07-11T08:30:00Z"
  },
  "qualification_info": {
    "score": 100.0,
    "status": "QUALIFIED",
    "reason": "gpay_structured_metadata",
    "evaluated_at": "2026-07-11T11:15:32Z"
  }
}
```

---

## 5. Source-Aware Qualification Strategy

Under V2, the qualification logic will become source-aware. Instead of applying text scoring universally, qualification is branched based on the signal source.

### 5.1 GPay & Bank Statement Signals (Structured)
* **Strategy**: Metadata-First.
* **Logic**: If the signal satisfies the minimum metadata contract, it is automatically qualified (`QUALIFIED` status, score `100.0`, reason `gpay_structured_metadata` / `bank_statement_structured_metadata`). If the metadata is incomplete, it falls back to text scoring.

### 5.2 SMS / WhatsApp Signals (Unstructured)
* **Strategy**: Rule-Based Scoring Engine (Preserved from V1).
* **Logic**: Applies age check, OTP/noise checks, telecom filters, ignore lists, family context boost, and high-value domain boost. Applies the financial preservation override if a low-scoring message has financial keywords.

---

## 6. Metadata Utilization Review

Below is the mapping and utility assessment of the parsed ingestion fields:

| Metadata Field | Current Usage | Proposed Usage | Qualification Impact | Downstream Impact |
|---|---|---|---|---|
| `amount` | Discarded | Preserved in `qualified_signals.amount` and metadata JSON. | Qualifies structured signals immediately. | Plugs into SUA contract directly without LLM extraction. |
| `currency` | Discarded | Preserved in `qualified_signals.currency` and metadata JSON. | None. | Direct mapping to contract. |
| `counterparty` | Discarded | Preserved in metadata JSON. | Used for validation. | Maps to contract merchant directly. |
| `transaction_type`| Discarded | Preserved in `qualified_signals.transaction_type` and metadata JSON. | Direct eligibility check. | Maps to transaction type (DEBIT/CREDIT). |
| `reference_number`| Discarded | Preserved in metadata JSON. | None. | Maps to transaction ID for deduplication. |
| `source_file_name`| Discarded | Preserved in metadata JSON. | None. | Preserves source lineage. |
| `source_file_hash`| Discarded | Preserved in metadata JSON. | None. | Used for file-level replay audits. |
| `source_ingested_at`| Discarded | Preserved in metadata JSON. | None. | Lineage timing validation. |
