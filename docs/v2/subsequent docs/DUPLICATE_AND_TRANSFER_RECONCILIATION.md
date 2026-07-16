# Duplicate & Transfer Reconciliation

## 1. Algorithmic Duplicate Reconciliation Matrix

To prevent double-counting across real-time feeds (SMS) and batch settlement files (GPay PDFs, bank statements), the ingestion engine applies deterministic matching rules.

---

## 2. Match Key Definition & Confidence Scores

Transactions are cross-referenced using three classes of matching keys:

| Match Category | Conditions for Match | Confidence Score | Action |
| :--- | :--- | :---: | :--- |
| **Exact Key Match** | Reference Number (UPI transaction ID, IMPS ref) is present in both records and is identical. | **1.00 (TRUE_DUPLICATE)** | Keep the PDF statement record (source of truth); suppress/link the SMS record. |
| **Fuzzy Key Match** | Amount is identical, and dates are within ±24 hours, and normalized merchants or counterparts match. | **0.90 (TRUE_DUPLICATE)** | Keep statement record; link/suppress SMS. |
| **Partial Event Match** | Date matches, amount matches, but narration differs (e.g. Mandate request vs Mandate registration). | **0.80 (PARTIAL_DUPLICATE)** | Group under single parent transaction. |
| **Related Event Match** | Transfer of Rs. X from Bank ➔ Wallet, followed by payment of Rs. Y (Y <= X) from Wallet ➔ Merchant. | **0.60 (RELATED_EVENT)** | Link transactions; do not delete either record. |
| **No Match** | No keys or fuzzy criteria match. | **0.00 (UNIQUE)** | Write new record to ledger. |

---

## 3. Duplicate Scanning Rules

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CROSS-CHANNEL DE-DUPLICATION                    │
├─────────────────┬──────────────────────────────────────────────────────┤
│ GPay ↔ SMS      │ - Match Key: UPI reference number.                   │
│                 │ - Window: ±24 hours.                                 │
│                 │ - Action: Suppress SMS; GPay is source of truth.     │
├─────────────────┼──────────────────────────────────────────────────────┤
│ Statement ↔ SMS │ - Match Key: IMPS / UPI / NEFT reference number.     │
│                 │ - Window: ±48 hours (statement may settle slowly).   │
│                 │ - Action: Suppress SMS; Statement is source of truth.│
├─────────────────┼──────────────────────────────────────────────────────┤
│ GPay ↔          │ - Match Key: Reference number / UPI transaction ID.  │
│ Statement       │ - Window: ±24 hours.                                 │
│                 │ - Action: Keep Statement (cleared balance anchor).   │
├─────────────────┼──────────────────────────────────────────────────────┤
│ SMS ↔ SMS       │ - Match Key: Message Hash (local deduplication) or   │
│                 │   amount + exact timestamp matching.                 │
│                 │ - Action: Drop second SMS; keep first.               │
└─────────────────┴──────────────────────────────────────────────────────┘
```

---

## 4. Internal Transfer & Self-Transfer Detection

Internal transfers move cash between user-owned accounts (e.g., HDFC ↔ SBI savings) and must not be categorized as income or expenses.

### A. Identification Rules
A transaction is flagged as an internal transfer if:
1. **Narration Match**: The transaction text matches one of the transfer patterns:
   - `HDFC TO SBI` / `SBI TO HDFC` / `TRANSFER TO SBI`
   - `SELF TRANSFER` / `OWN A/C` / `TFR FROM OWN`
2. **Owner Name Match**: The sender or receiver string matches the user's registered name:
   - `PRADEEP PANNEERSELVAM` / `PRADEEP P`
   - `SHOBANA`
3. **Double-Entry Offset Match**: A debit from HDFC matches a credit to SBI for the same amount within a 1-hour window.

### B. Confidence Scoring Matrix
- **Confidence = 1.00**: Matches **Rule 1** (explicit transfer keywords in statement/SMS).
- **Confidence = 0.95**: Matches **Rule 2** (sender or receiver matches owner name).
- **Confidence = 0.90**: Matches **Rule 3** (exact double-entry offsetting transaction within 1 hour).

### C. Examples of Transfer Reconciliation
1. **Scenario 1 (HDFC to SBI)**:
   - *HDFC Statement row*: Debit Rs. 25,000 to SBI on 30-Apr.
   - *SBI Statement row*: Credit Rs. 25,000 from HDFC on 30-Apr.
   - *Action*: The engine matches these two rows via **Rule 3** (offset) and **Rule 1** (narration references HDFC/SBI). Both records are flagged as `is_self_transfer = True`, and their Category is set to `Transfer`. The net expense impact in reports is Rs. 0.00.
