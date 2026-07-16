# Internal Transfer & Self-Transfer Analysis

## Executive Summary
Self-transfers represent movement of funds between accounts owned by the same user. Treating these movements as expenses artificially inflates outbound spending statistics and distorts net income calculations. This document details self-transfer patterns in our dataset and provides exact detection heuristics.

---

## 1. Identified Self-Transfer Examples

Our database and statement audit revealed two primary self-transfer patterns:

### Pattern A: Inter-Account Transfer (IMPS/NEFT/UPI)
Direct transfer of funds from Bank A to Bank B (e.g. HDFC to SBI).

- **Example 1 (SMS database)**:
  - `Received! INR 6,500.00 in HDFC Bank A/c xx4147 On 29-05-26 For IMPS -PRADEEP PANNEERSELVAM- FTIMPS76...`
  - `Received! INR 10,500.00 in HDFC Bank A/c xx4147 On 29-05-26 For IMPS -PRADEEP PANNEERSELVAM- FTIMPS7...`
  - **Analysis**: The sender name is "PRADEEP PANNEERSELVAM", which is the account owner's name. This is a classic self-transfer (incoming IMPS from own account).

- **Example 2 (Statement PDF)**:
  - `30/04/2026 WDL TFR FIRDFTFRREF: 235870087933192953K580035 0045134797859 OF Mr. PRADEEP P AT 12247 ACB RAMANPUDUR - 25,000.00`
  - **Analysis**: A withdrawal of Rs. 25,000 transferred to a user's own destination account.

### Pattern B: Wallet Loads & Settlement
- **Example**:
  - `30/06/2026 DEP TFR IMPS/618115599021/PAYTM/PRADEEP P - - 10,000.00`
  - **Analysis**: Loading Rs. 10,000 into a Paytm Wallet from an HDFC account. The cash did not leave the user's possession; it merely moved from HDFC Bank to the Paytm Wallet asset.

---

## 2. Detection Signals & Confidence Rules

To prevent self-transfers from becoming expenses, the Financial Agent V1 must implement the following rule structure:

```
┌─────────────────────────────────────────────────────────────┐
│                 SELF-TRANSFER CONFIDENCE RULES              │
├───────────────────┬─────────────────────────────────────────┤
│ Rule 1:           │ Narration contains "Self Transfer to",  │
│ Direct keywords   │ "OWN A/C", or "TFR TO [Bank Name]".     │
│                   │ Confidence: 100% (CRITICAL)             │
├───────────────────┼─────────────────────────────────────────┤
│ Rule 2:           │ Transfer message has sender or receiver │
│ Owner Name Match  │ equal to user's name (e.g. "PRADEEP" /  │
│                   │ "SHOBANA" in transfer remarks).         │
│                   │ Confidence: 95% (HIGH)                  │
├───────────────────┼─────────────────────────────────────────┤
│ Rule 3:           │ Double-Entry Matching:                  │
│ Cross-Bank Link   │ Credit of Rs. X in Bank A within 1 hour │
│                   │ of a Debit of Rs. X in Bank B.          │
│                   │ Confidence: 90% (MEDIUM)                │
└───────────────────┴─────────────────────────────────────────┘
```

---

## 3. Recommended Ledger Structure
Self-transfers must be recorded as **TRANSFER** type in the transaction ledger:
- Debit Row: Account = `SBI Savings`, Amount = `-25,000`, Type = `TRANSFER`, Destination = `HDFC Savings`.
- Credit Row: Account = `HDFC Savings`, Amount = `+25,000`, Type = `TRANSFER`, Source = `SBI Savings`.

Both sides of the transfer reconcile to `0` net expense, keeping cash flow reports and expense analytics perfectly clean.
