# Duplicate Transaction Analysis

## Overview
Duplicate entries represent the single greatest risk to ledger integrity in personal finance platforms. This document presents a duplicate transaction audit across all active ingestion channels in Jarvis: GPay statements, SBI statement PDFs, and financial SMS alerts.

---

## 1. Concrete Duplicate Examples & Matches

### Case 1: GPay PDF vs. Bank Statement PDF
The GPay statement and the Bank Statement contain overlapping entries because GPay acts as the payment initiator, while the bank acts as the settlement entity.

- **Example 1 (IMPS/UPI Transfer)**:
  - **GPay Record**: `Paid to Anusha Sampath` on **08 May, 2026** (Amount: **INR 20,000.00**).
  - **Bank Statement Record**: `WDL TFR IMPS/612809511819/HDFC-xx221-Pradeep/Transfer 0098294162096` on **08/05/2026** (Amount: **INR 20,000.00**).
  - **Relationship**: **TRUE_DUPLICATE**. Both represent a single physical movement of cash settled via IMPS on May 8th.

- **Example 2 (UPI Merchant Purchase)**:
  - **GPay Record**: `Paid to kalai chelvi` on **28 Jun, 2026** (Amount: **INR 1,000.00**).
  - **Bank Statement Record**: `WDL TFR IMPS/617805648112/HDFC-xx221-Pradeep/Transfer` on **27/06/2026** (Amount: **INR 1,000.00**).
  - **Relationship**: **TRUE_DUPLICATE**. Minor 24-hour settlement delay in posting dates.

### Case 2: SMS vs. GPay PDF
- **Example (Pharmacy purchase)**:
  - **SMS Record**: `Dear SHOBANAKUMAR, Thank you for your purchase @ Apollo Pharmacy.` (Amount: **INR 140.81**).
  - **GPay Record**: `Paid to 15966 Apollo Pharmacy` on **15 Jun, 2026** (Amount: **INR 140.81**).
  - **Relationship**: **TRUE_DUPLICATE**.

### Case 3: Multiple SMS Alerts for Same Event
- **Example (Mandate Setup)**:
  - **SMS 1**: `Mandate Set Rs.50000.00 For ETMONEY From HDFC Bank A/c x4147 UMN: f0082d7f8e2a4f`
  - **SMS 2**: `Congratulations! Automatic payment of Rs.50,000 for Etmoney has been setup successfully.`
  - **Relationship**: **PARTIAL_DUPLICATE** (Related Event). Represents a single mandate registration event reported by HDFC Bank and Paytm App respectively.

---

## 2. Duplicate Classification Taxonomy

All duplicates must be classified into one of the following lanes to prevent ledger pollution:

```
┌────────────────────────────────────────────────────────┐
│                      LANE CLASSIFICATION               │
├───────────────────┬────────────────────────────────────┤
│ TRUE_DUPLICATE    │ Same amount, same date (±24h),     │
│                   │ overlapping reference or context.  │
│                   │ ACTION: Keep one, suppress others. │
├───────────────────┼────────────────────────────────────┤
│ PARTIAL_DUPLICATE │ Same event described differently,  │
│                   │ (e.g. Mandate alert + setup SMS)   │
│                   │ ACTION: Group into single event.   │
├───────────────────┼────────────────────────────────────┤
│ RELATED_EVENT     │ Cash movement linked to expense    │
│                   │ (e.g. Wallet load → purchase)      │
│                   │ ACTION: Link transactions,         │
│                   │ tag as transfer, not expense.      │
├───────────────────┼────────────────────────────────────┤
│ UNIQUE            │ Independent transaction.           │
│                   │ ACTION: Insert to ledger.          │
└───────────────────┴────────────────────────────────────┘
```

---

## 3. De-duplication Reconciliation Strategy

To prevent double-counting when building Financial Agent V1, the ingestion engine must apply these rules:
1. **Reference-based Deduplication**: Match on UPI Reference / UMN (Unique Mandate Number) first. Since these are globally unique, a match is a 100% confidence duplicate.
2. **Fuzzy Context Matching**: If reference numbers are missing (e.g. standard SMS alerts), group by:
   - `Amount`: Exact match (tolerance = 0.0).
   - `Timestamp`: Within a 48-hour window.
   - `Contextual Overlap`: String matching on merchant keywords (e.g. `Apollo` in SMS and `Apollo Pharmacy` in GPay).
