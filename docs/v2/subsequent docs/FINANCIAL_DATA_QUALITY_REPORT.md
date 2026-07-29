# Financial Data Quality Report

## Overview
This report evaluates the accuracy, cleanliness, and completeness of the financial records in the Jarvis system. Based on our audit of 132 classified SMS signals, 278 GPay PDF rows, and 49 bank statement rows, we identify severe data quality concerns that must be addressed before launching Financial Agent V1.

---

## 1. Field Completeness Audit
The completeness of extracted fields differs significantly across channels:

| Ingestion Channel | Amount | Currency | Timestamp | Counterparty | Ref Number | Transaction Type |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **PDF Statements** | 100% | 100% | 100% | 98% | 85% | 100% |
| **Financial SMS** | 100% | 97.7% | 100% | 2.2% | 15% | 100% |

> [!WARNING]
> **Counterparty (Merchant) Extraction is Broken on SMS**:
> While SMS alerts contain clear amounts and transaction types (e.g. DEBIT/CREDIT), the `merchant` or `counterparty` field was successfully extracted in only **2.27% of signals** (Apollo Pharmacy / Amazon). For the rest, the LLM left them blank or mapped them to `None`. 
> Building expense analytics on SMS data will result in "Unknown Merchant" representing 98% of categorized transactions.

---

## 2. Marketing Spam Leakage (Critical Severity)
A deep audit of the 132 `FINANCIAL` signals in `understood_signals` revealed that **99 signals (75%) are actually marketing spam or credit card promotions** rather than actual transactions.

### Examples of Spam Leaking into the Financial Ledger:
- `Congrats! Claim your Lifetime Free HDFC Bank Credit Card+Upto Rs.2750 Amazon Voucher...` (Repeated 46 times!)
- `Don't miss your 100% Guaranteed* Lifetime FREE HDFC Bank Credit Card with a limit Rs.75000...` (Repeated 9 times!)
- `Dear SBI User, your A/c X4264 is eligible for a pre-approved loan of...`

> [!CAUTION]
> **Spam Pollution Risk**:
> If Financial Agent V1 ingest these rows directly into the transaction ledger without pre-filtering, they will create phantom credits/debits (e.g. adding Rs. 75,000 credit limit or Rs. 2,750 voucher as income/assets). 
> SMS inputs must undergo strict transaction confirmation filtering before ledger writing.

---

## 3. Discovered Statement Parser Bugs

1. **SBI multi-page scanning issue**: The parser does not exit when encountering multiple page headers, discarding early transaction blocks in multi-page statement PDFs.
2. **Partial parsing failures**: If a line contains multi-line descriptions (e.g., NEFT references split across two lines in the PDF), the second line is sometimes discarded or parsed as a new empty transaction.

---

## 4. Recommended Data Quality Safeguards

To transition successfully to Financial Agent V1, the system must deploy three safeguards:
1. **SMS Transaction Type Guard**: Drop any SMS that is not explicitly marked as `DEBIT` or `CREDIT` (this automatically filters out the 99 UNKNOWN marketing offers).
2. **Fuzzy Merchant Mapping**: Implement a mapping dictionary to clean and normalize merchant variants (e.g., `SWIGGY`, `SWIGGY LTD`, `SWIGGYBANGALORE` -> `Swiggy`).
3. **Double-Entry Reconciliation Pipeline**: Use statements as the single source of truth for historical balances, using SMS alerts as real-time notifications that are automatically resolved/merged when the monthly statement is uploaded.
