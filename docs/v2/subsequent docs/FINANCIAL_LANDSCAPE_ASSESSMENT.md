# Financial Landscape & Data Normalization Assessment

## Executive Summary
This document provides a complete landscape assessment of the financial-related data currently stored in Jarvis. Our discovery and analysis was performed on the active Supabase schema and files, auditing raw mobile signals, classified SMS items, and statement PDFs.

---

## 1. Source Inventory & Counts

An audit of the `processed_files` and `mobile_signals` tables shows the following source breakdown:

| Source Type | Source File / Format | Raw Signals Count | Extracted Transactions |
| :--- | :--- | :---: | :---: |
| **GPay PDF** | `gpay_statement_20260401_20260630.pdf` | 1 | 278 |
| **Bank Statement** | `Email_Statement_080720262113519349631.pdf` | 1 | 49 |
| **Financial SMS** | SMS signals in `mobile_signals` / `understood_signals` | 441 | 132 |
| **WhatsApp SMS** | WhatsApp signals in `mobile_signals` | 2 | 0 |

---

## 2. Date Ranges & Temporal Coverage

The dataset shows a clear division in terms of timeline coverage across channels:

- **Periodic Statements (PDFs)**:
  - **GPay Statement**: Covers **2026-04-01 to 2026-06-30** (Q1/Q2 calendar cycles).
  - **SBI Bank Statement**: Covers **2026-04-01 to 2026-06-30** (Q1/Q2 calendar cycles).
- **Real-Time Feed (SMS)**:
  - **SMS / Mobile Signals**: Covers **2026-07-01 to 2026-07-12** (Active real-time window).

> [!IMPORTANT]
> **Temporal Coverage Gap**:
> There is a complete gap in statement coverage for the month of **July 2026**. Conversely, there is no real-time SMS coverage in the database for **April, May, and June 2026**. This creates two distinct zones:
> 1. **Historical Ledger Zone (Apr - Jun)**: Driven purely by statement imports.
> 2. **Real-time Ledger Zone (Jul)**: Driven purely by SMS alerts.

---

## 3. Discovered Parser Issues & Gaps
During this Phase 0 assessment, a critical production bug was discovered in the SBI statement parser (`parse_sbi_text` in [bank_statement_collector.py](file:///home/prad/petprojects/ai/jarvis/src/agents/consumer/collectors/bank_statement_collector.py#L7-L87)):
- **Bug**: The parser loops through lines to find the transaction table start index `start_idx`. However, it does not `break` upon finding the first occurrence. In multi-page statements, the word `Balance` occurs on every page header/footer, causing `start_idx` to continually overwrite to the end of the file, skipping the actual transactions.
- **Impact**: All transactions prior to the final page were dropped. Correcting this block yields the actual **49 transactions** recorded above.

---

## 4. Key Discovery Findings for Financial Agent V1

1. **SMS is highly noisy**: Over **75% of FINANCIAL-classified SMS** signals are actually marketing spam or credit card promotions rather than real ledger transactions.
2. **Periodic vs. Real-Time Reconciliation**: GPay and Bank statement files act as delayed sources of truth. The system needs to merge live SMS alerts (which trigger instantly) with periodic statement uploads (which arrive days/weeks later) without creating double-entries.
3. **Reference Linking**: UPI transaction IDs (`UPITransactionID:` or 12-digit UPI reference numbers) are present in both GPay statements and HDFC/SBI bank alerts, providing a unique key to link records across channels.
