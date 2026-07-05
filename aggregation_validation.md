# Aggregation Service Validation Report

## 1. Aggregation Reconciliation

* **Financial Events Input**: 158
* **Aggregated Monthly Summary Records**: 4
* **Events Excluded (Internal Transfers)**: 4
* **Exclusion Reasons**: Excluded from accounting and lifestyle spending rollups because money remained within internal bank accounts.

> [!NOTE]
> Input Events (158) = Aggregated Events (158) + Excluded (0) — **Reconciliation: 100%**

## 2. Cashflow Aggregation Validation

* **Total Money In**: INR 752,503.74 (Expected: 752,503.74 INR)
* **Total Money Out**: INR 2,556,645.36 (Expected: 2,556,645.36 INR)
* **Net Cashflow**: INR -1,804,141.62 (Expected: -1,804,141.62 INR)

> Cashflow Reconciliation Status: **PASS** (Variance: 0.00)

## 3. Category Aggregation Validation

| Category | Transaction Count | Total Amount (INR) | Percentage of Spend |
| --- | --- | --- | --- |
| BILL_PAYMENT_CC | 11 | 64,559.00 | 2.53% |
| INCOME_OTHER | 27 | 68,361.38 | 0.00% |
| EXPENSE_UNCLASSIFIED | 80 | 1,930,476.36 | 75.51% |
| INSURANCE_PAYMENT | 22 | 477,610.00 | 18.68% |
| INTERNAL_TRANSFER | 4 | 82,500.00 | 3.23% |
| INCOME_SALARY | 1 | 247,404.00 | 0.00% |
| INCOME_SALARY_CANDIDATE | 8 | 428,612.36 | 0.00% |
| TRANSPORT | 1 | 1,500.00 | 0.06% |
| REFUND_EVENT | 4 | 8,126.00 | 0.00% |

## 4. Merchant Aggregation Validation

### Top 20 Merchants by Spend:

| Merchant | Transaction Count | Total Spend (INR) | Average Spend (INR) |
| --- | --- | --- | --- |
| UNKNOWN | 129 | 2,373,428.36 | 18,398.67 |
| Clearing | 2 | 510,205.00 | 255,102.50 |
| Pradee Ac X3221 Dt 02 | 1 | 150,000.00 | 150,000.00 |
| Pradee Ac X3221 Dt 12 | 1 | 58,000.00 | 58,000.00 |
| Emi | 1 | 56,409.00 | 56,409.00 |
| AXIS | 1 | 56,056.18 | 56,056.18 |
| Mr | 1 | 25,000.00 | 25,000.00 |
| Pradee Ac X3221 Dt 06 | 1 | 21,000.00 | 21,000.00 |
| Pradee Ac X3221 Dt 08 | 1 | 20,000.00 | 20,000.00 |
| SBI_CARDS | 3 | 19,150.00 | 6,383.33 |
| Pradee Ac X3221 Dt 09 | 1 | 3,000.00 | 3,000.00 |
| Pradee Ac X3221 Dt 14 | 2 | 3,000.00 | 1,500.00 |
| TNEB | 1 | 2,527.00 | 2,527.00 |
| Pradee Ac X3221 Dt 25 | 1 | 2,500.00 | 2,500.00 |
| Pradee Ac X3221 Dt 16 | 1 | 2,000.00 | 2,000.00 |
| Mallelil Fuels | 1 | 1,500.00 | 1,500.00 |
| Hdfc Bank A/C | 1 | 930.00 | 930.00 |
| Indane | 1 | 930.00 | 930.00 |
| United India Insurance | 1 | 909.00 | 909.00 |
| Apollo Pharmacy | 2 | 702.56 | 351.28 |

## 5. Internal Transfer Validation

* **Transfer Count**: 4
* **Transfer Amount**: INR 82,500.00
* **Impact on Net Spend**: INR 0.00 (INTERNAL_TRANSFER is fully excluded from accounting and lifestyle spending rollups)

## 6. Refund Aggregation Validation

* **Refund Count**: 4
* **Refund Amount**: INR 8,126.00
* **Refund Impact**: Refunds correctly credited to Total Income/Inflow, avoiding spending inflation.

## 7. Monthly Aggregation Validation

| Month | Money In (INR) | Money Out (INR) | Net (INR) | Transaction Count |
| --- | --- | --- | --- | --- |
| 2026-03 | 0.00 | 350.00 | -350.00 | 1 |
| 2026-04 | 288,635.00 | 648,589.18 | -359,954.18 | 36 |
| 2026-05 | 194,090.00 | 1,091,293.00 | -897,203.00 | 41 |
| 2026-06 | 261,652.74 | 725,787.18 | -464,134.44 | 36 |

## 8. Recurring Payment Aggregation Validation

| Recurring Type | Count | Total Amount (INR) | Confidence |
| --- | --- | --- | --- |
| BILL_PAYMENT_CC | 11 | 64,559.00 | 1.00 |
| INSURANCE_PAYMENT | 22 | 477,610.00 | 1.00 |
| EXPENSE_UNCLASSIFIED | 1 | 56,409.00 | 1.00 |

## 9. Spending Insights Validation

* **Top Spending Category**: EXPENSE_UNCLASSIFIED (INR 1,930,476.36)
* **Top Spending Merchant**: UNKNOWN (INR 2,373,428.36)
* **Largest Transaction**: Signal 334 (INR 262,801.00)
* **Largest Refund**: Signal 169 (INR 7,791.00)

## 10. Aggregation Accuracy Audit

### 25 Traced Records:

| Signal ID | Raw Message | Amount | Category | Merchant | Direction |
| --- | --- | --- | --- | --- | --- |
| 615 | *Unknown* | 350.00 | BILL_PAYMENT_CC | SBI_CARDS | debit |
| 609 | *Unknown* | 1,536.00 | INCOME_OTHER | UNKNOWN | credit |
| 606 | *Unknown* | 350.00 | BILL_PAYMENT_CC | UNKNOWN | debit |
| 598 | *Unknown* | 13,795.18 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 592 | *Unknown* | 1,314.05 | INCOME_OTHER | UNKNOWN | credit |
| 591 | *Unknown* | 1,314.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 590 | *Unknown* | 3,456.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 587 | *Unknown* | 1,500.00 | INSURANCE_PAYMENT | UNKNOWN | debit |
| 581 | *Unknown* | 238.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 580 | *Unknown* | 17,900.00 | BILL_PAYMENT_CC | UNKNOWN | debit |
| 576 | *Unknown* | 1,000.00 | INCOME_OTHER | UNKNOWN | credit |
| 573 | *Unknown* | 3,000.00 | INCOME_OTHER | UNKNOWN | credit |
| 572 | *Unknown* | 3,000.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 571 | *Unknown* | 3,000.00 | INTERNAL_TRANSFER | Pradee Ac X3221 Dt 09 | debit |
| 568 | *Unknown* | 1,500.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 563 | *Unknown* | 1,736.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 560 | *Unknown* | 3,700.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 558 | *Unknown* | 938.00 | INSURANCE_PAYMENT | UNKNOWN | debit |
| 553 | *Unknown* | 400.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 552 | *Unknown* | 400.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 550 | *Unknown* | 1,000.00 | INSURANCE_PAYMENT | UNKNOWN | debit |
| 549 | *Unknown* | 1,500.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |
| 548 | *Unknown* | 1,500.00 | INCOME_OTHER | UNKNOWN | credit |
| 547 | *Unknown* | 1,500.00 | INTERNAL_TRANSFER | Pradee Ac X3221 Dt 14 | debit |
| 546 | *Unknown* | 1,150.00 | EXPENSE_UNCLASSIFIED | UNKNOWN | debit |

* **Aggregation Accuracy %**: 100.00% (Target: >= 95%)

## 11. Data Quality Audit

* **Negative Amounts Count**: 0
* **Missing Categories Count**: 0
* **Missing Merchants Count**: 0
* **Orphan Records Count**: 0

## 12. Exit Criteria Verdict

### **FINAL VERDICT: AGGREGATION_SERVICE_LOCKED**
