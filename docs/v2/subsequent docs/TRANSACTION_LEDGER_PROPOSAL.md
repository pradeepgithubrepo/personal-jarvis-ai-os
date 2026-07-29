# Transaction Ledger Proposal

## 1. Canonical Transaction Schema

This document details the database schema and canonical fields designed for the `financial_ledger` table. All incoming financial records (SMS alerts, GPay statement PDFs, SBI statements) will be normalized into this structure before storage.

---

## 2. Field Specifications & Definitions

### A. Mandatory Fields
These fields represent the fundamental attributes of a transaction. A row cannot be inserted without them.

| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `transaction_id` | `UUID` | Primary Key. Globally unique identifier. |
| `event_date` | `TIMESTAMPTZ` | The date and time when the transaction physically occurred (adjusted to UTC). |
| `amount` | `NUMERIC(12, 2)` | The absolute decimal value of the transaction (must be positive). |
| `currency` | `VARCHAR(3)` | 3-character ISO currency code (default: `INR`). |
| `direction` | `VARCHAR(6)` | Enum: `DEBIT` (money leaving) or `CREDIT` (money entering). |
| `source` | `VARCHAR(20)` | Enum: `SMS`, `GPAY_PDF`, `BANK_STATEMENT_PDF`, representing the source channel. |
| `source_ref_id` | `UUID` | Foreign key referencing the raw source signal in `mobile_signals` / `understood_signals`. |

### B. Optional Fields
These fields capture additional metadata that may not be present in all sources (e.g. merchant names or reference IDs).

| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `raw_narration` | `TEXT` | The raw, uncleaned text string from the SMS message or statement row. |
| `reference_number` | `VARCHAR(64)` | Unique transaction identifier from the payment network (e.g. 12-digit UPI transaction ID, IMPS code). |
| `merchant` | `VARCHAR(100)` | The normalized name of the payee/payer (e.g. `Swiggy`, `Amazon`). |
| `counterparty` | `VARCHAR(150)` | The raw counterparty string before normalization (e.g. `SWIGGY*BANGALORE`). |
| `category` | `VARCHAR(30)` | The category classification (e.g. `Food`, `Travel`, `Utilities`). |
| `confidence` | `NUMERIC(3, 2)` | Confidence score of parsing and classification (range: `0.00` to `1.00`). |

### C. Derived & System Fields
These fields are computed or managed by the database/application logic.

| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `is_self_transfer` | `BOOLEAN` | True if the transaction is matched as an internal transfer. Derived from double-entry offsets and name keywords. |
| `is_override` | `BOOLEAN` | True if the merchant, category, or transfer flag has been manually modified by the user. |
| `created_at` | `TIMESTAMPTZ` | Timestamp when the record was first inserted into the ledger. |
| `updated_at` | `TIMESTAMPTZ` | Timestamp when the record was last modified. |

---

## 3. Database Constraints

To protect the ledger from corrupt data and double-counting, we enforce the following check constraints:

```sql
-- Ensure amount is strictly positive
CONSTRAINT chk_positive_amount CHECK (amount > 0.00);

-- Enforce currency format
CONSTRAINT chk_currency_format CHECK (length(currency) = 3);

-- Enforce direction values
CONSTRAINT chk_direction_enum CHECK (direction IN ('DEBIT', 'CREDIT'));

-- Enforce source values
CONSTRAINT chk_source_enum CHECK (source IN ('SMS', 'GPAY_PDF', 'BANK_STATEMENT_PDF'));

-- Unique reference number constraint to prevent double insertions of the same payment event
CONSTRAINT unique_reference_number UNIQUE (reference_number);
```
