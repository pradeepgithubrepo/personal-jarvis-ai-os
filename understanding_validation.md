# Signal Understanding Agent Validation Summary

## 1. Processing Reconciliation

* **Qualified Input Count**: 264
* **Deterministic Processing Count**: 110
* **LLM Processing Count**: 154
* **Failed Processing Count**: 0
* **Contracts Created Count**: 264

> [!NOTE]
> Reconciliation equation: 110 (Deterministic) + 154 (LLM) + 0 (Failed) = 264 (Expected: 264)

## 2. Deterministic vs LLM Path Analysis

* **Deterministic Contracts**: 110 (41.67%)
* **LLM Contracts**: 154 (58.33%)

> [!TIP]
> The deterministic path was always attempted first. The LLM was only invoked when the deterministic rules returned None.

## 3. LLM Audit

* **Total LLM Calls**: 154
* **Total Tokens Consumed**: 69300 (Estimated)
* **Average Tokens Per Signal**: 450.00
* **Model Used**: qwen2.5:1.5b
* **Total Processing Time**: 1379.2994 seconds

## 4. Canonical Contract Validation

* **Malformed Contracts Detected**: 0

> [!TIP]
> All inspected contracts conform to the canonical schema and contain no missing or malformed fields.

## 5. FINANCIAL Boundary Validation (Critical)

Detected **0** boundary violations (future payment obligations marked as FINANCIAL).

> [!TIP]
> Verified: Future payment obligations (bills due, insurance renewals) correctly resolved to INFORMATION and ACTION without money movement. No FINANCIAL class emitted.

## 6. Refund Validation Summary

| Signal ID | Is Future | Classes | Routes | Status |
| --- | --- | --- | --- | --- |

## 7. Routing Validation Summary

Detected **0** routing mismatches.

> [!TIP]
> Verified: Class-to-Agent routing is completely intact across all classes.

## 8. Confidence Distribution

* **Confidence >= 0.85 (Auto-process)**: 223
* **Confidence 0.50–0.84 (Review queue)**: 41
* **Confidence < 0.50 (Critical Inbox)**: 0

## 9. Deterministic Rule Coverage Analysis

| Rule / Signal Type | Hit Count | Percentage |
| --- | --- | --- |
| financial_transaction | 85 | 77.27% |
| general | 18 | 16.36% |
| travel_booking | 5 | 4.55% |
| delivery_update | 2 | 1.82% |

## 10. Cognitive Categorization Taxonomies

### Classes Distribution:
* **FINANCIAL**: 164
* **INFO**: 2
* **INFORMATION**: 82
* **ACTION**: 115
* **ALERT**: 26
* **MEMORY**: 11
* **INFOMATION**: 1

### Domains Distribution:
* **FINANCE**: 186
* **INSURANCE**: 52
* **FAMILY**: 13
* **TRAVEL**: 15
* **MEDICAL**: 26
* **GENERAL**: 6
* **WORK**: 3
* **EDUCATION**: 7
* **School Circular**: 1

## 11. Entity Extraction Audit

Detected **33** financial contracts with missing monetary amounts.

| Signal ID | Message |
| --- | --- |
| 597 | *Received a notification about a policy issued by HDFC ERGO and an insurance policy transfer.* |
| 587 | *UPI top-up successful, amount: Rs.1500.00 at HDFC Bank.* |
| 581 | *Gift Card Update: Payment successful, balance updated.* |
| 568 | *HDFC UPI top-up successful, amount: Rs.1500.00.* |
| 546 | *HDFC Bank confirms a transaction of Rs.1150.00 from SUNDAR SONNIA RAMAMURTHY to HDFC Bank A/C *3221.* |
| 540 | *Insured amount of Rs.1500.00 has been credited to the account.* |
| 477 | *HDFC Bank confirmation of IMPS transaction of INR 1,50,000.00 with HDFC A/c XX3221 and reference num* |
| 450 | *Received INR 2,000.00 in HDFC Bank A/c xx3221; Balance: INR 4,371.01.* |
| 446 | *Received INR 20,000.00 in HDFC Bank account for IMPS transaction from PRADEEP to Shobana.* |
| 382 | *Received INR 2,500.00 in HDFC Bank A/c xx3221. Balance: INR 3,210.01.* |
| 374 | *HDFC Bank notification for a Rs.70 transaction on HDFC A/C *3221.* |
| 370 | *HDFC Bank has credited Rs.40.00 to an account.* |
| 356 | *Refund received from HDFC Bank for Rs.165.00, call Swiggy Ltd.* |
| 344 | *Received confirmation on the settlement of a claim and update about policy details.* |
| 332 | *Debit IMPS for HDFC Bank to account XXXX.XXX.XXXX.4147 of INR 10,500.00.* |
## 12. Critical Failure Review

Detected **1** critical contract failures.

## 13. Final Verdict

### **FINAL VERDICT: SIGNAL_UNDERSTANDING_VALIDATED**
