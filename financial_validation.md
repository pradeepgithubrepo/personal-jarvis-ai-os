# Financial Agent Validation Report

## 1. Reconciliation Validation

* **Total Financial Contracts**: 158
* **Total Debit Events**: 118
* **Total Credit Events**: 36
* **Total Refund Events**: 4
* **Total Unknown/Adjustment Events**: 0

> [!NOTE]
> Reconciliation check: 118 (Debit) + 36 (Credit) + 4 (Refund) + 0 (Unknown) = 158 (Expected: 158) — **PASS**

## 2. Financial Classification Validation

* **Inspected Classifications**: 158
* **Correct Classifications**: 158
* **Accuracy %**: 100.00% (Target: > 80%)

## 3. Cashflow Validation

* **Total Money In**: INR 752,503.74
* **Total Money Out**: INR 2,556,645.36
* **Net Cashflow**: INR -1,804,141.62

### Sample Inflows (Up to 20):

| Signal ID | Merchant | Amount | Summary |
| --- | --- | --- | --- |
| 609 | UNKNOWN | INR 1,536.00 | *Received a financial transaction from HDFC Bank, Rs. 1536.00.* |
| 592 | UNKNOWN | INR 1,314.05 | *Received a debit from HDFC Bank A/C *3221.* |
| 576 | UNKNOWN | INR 1,000.00 | *Received Rs.1000.00 from HDFC Bank for Mr VELMURUGAN V's account.* |
| 573 | UNKNOWN | INR 3,000.00 | *Received INR 3,000.00 in HDFC Bank A/c xx3221 for IMPS- PRADEEP P-609916501529 with current balance of INR 3,380.98.* |
| 548 | UNKNOWN | INR 1,500.00 | *Received INR 1,500.00 in HDFC Bank A/c xx3221 with balance of INR 2,880.98.* |
| 541 | UNKNOWN | INR 2,500.00 | *Received INR 2,500.00 in HDFC Bank A/c xx3221.* |
| 540 | UNKNOWN | INR 1,500.00 | *Insured amount of Rs.1500.00 has been credited to the account.* |
| 537 | UNKNOWN | INR 13,730.98 | *Received INR 11,000.00 in HDFC Bank Account xx3221 for IMPS -PRADEEP P-.* |
| 510 | UNKNOWN | INR 149.97 | *Received Rs.149.97 from HDFC Bank A/C *3221, call to cancel the transaction blocked.* |
| 497 | Clearing | INR 247,404.00 | *Deposit of INR 2,47,404.00 received in HDFC Bank account for salary on 30-APR-26, updating current balance.* |
| 487 | UNKNOWN | INR 15,000.00 | *Received INR 15,000.00 in HDFC Bank A/c xx3221; updated account balance to INR 20,389.01.* |
| 450 | UNKNOWN | INR 2,000.00 | *Received INR 2,000.00 in HDFC Bank A/c xx3221; Balance: INR 4,371.01.* |
| 446 | UNKNOWN | INR 20,000.00 | *Received INR 20,000.00 in HDFC Bank account for IMPS transaction from PRADEEP to Shobana.* |
| 429 | UNKNOWN | INR 2,000.00 | *Received a bill of INR 2,000.00 in HDFC Bank for the account xx3221. The current balance is INR 2,344.01.* |
| 382 | UNKNOWN | INR 2,500.00 | *Received INR 2,500.00 in HDFC Bank A/c xx3221. Balance: INR 3,210.01.* |
| 378 | UNKNOWN | INR 520.00 | *Received Rs.520.00 from HDFC Bank A/C *3221 for Ref # 123560763831.* |
| 363 | UNKNOWN | INR 85.00 | *HDFC Bank payment received of Rs.85.00 from RETHINASWAMY C.* |
| 356 | Swiggy | INR 165.00 | *Refund received from HDFC Bank for Rs.165.00, call Swiggy Ltd.* |
| 344 | LIC | INR 555.00 | *Received confirmation on the settlement of a claim and update about policy details.* |
| 333 | UNKNOWN | INR 145,000.00 | *HDFC Bank transaction: INR 1,45,000.00 received on 29-05-26.* |

### Sample Outflows (Up to 20):

| Signal ID | Merchant | Amount | Summary |
| --- | --- | --- | --- |
| 615 | SBI_CARDS | INR 350.00 | *Transaction of INR 350.0 at sbi cards and paymen* |
| 606 | UNKNOWN | INR 350.00 | *Transaction of INR 350.0 at your sbi card ending with 69 on 31-mar-26* |
| 598 | UNKNOWN | INR 13,795.18 | *Transaction of INR 13795.18 at AD-SBICRD-S* |
| 591 | UNKNOWN | INR 1,314.00 | *Transaction of INR 1314.0 at JX-HDFCBK-S* |
| 590 | UNKNOWN | INR 3,456.00 | *Transaction of INR 3456.0 at VM-SBICRD-S* |
| 587 | UNKNOWN | INR 1,500.00 | *UPI top-up successful, amount: Rs.1500.00 at HDFC Bank.* |
| 581 | UNKNOWN | INR 238.00 | *Gift Card Update: Payment successful, balance updated.* |
| 580 | UNKNOWN | INR 17,900.00 | *Transaction of INR 17900.0 at your sbi card ending with 69 on 04-apr-26* |
| 572 | UNKNOWN | INR 3,000.00 | *Transaction of INR 3000.0 at VA-SBIPSG-T* |
| 571 | Pradee Ac X3221 Dt 09 | INR 3,000.00 | *Transaction of INR 3000.0 at pradee ac x3221 dt 09* |
| 568 | UNKNOWN | INR 1,500.00 | *HDFC UPI top-up successful, amount: Rs.1500.00.* |
| 563 | UNKNOWN | INR 1,736.00 | *Transaction of INR 1736.0 at BT-SBICRD-S* |
| 560 | UNKNOWN | INR 3,700.00 | *Transaction of INR 3700.0 at your sbi credit card* |
| 558 | UNKNOWN | INR 938.00 | *Transaction of INR 938.0 at 5676791* |
| 553 | UNKNOWN | INR 400.00 | *Transaction of INR 400.0 at AD-HDFCBK-S* |
| 552 | UNKNOWN | INR 400.00 | *DUE: Rs.400.00 from HDFC Bank A/C *3221 to SHOBANA KUMARI  P, Ref # 121565517477.* |
| 550 | UNKNOWN | INR 1,000.00 | *UPI LITE top-up amount of Rs.1000.00 successful, Ref No: 610494192568 at HDFC Bank.* |
| 549 | UNKNOWN | INR 1,500.00 | *Transaction of INR 1500.0 at AX-SBIPSG-T* |
| 547 | Pradee Ac X3221 Dt 14 | INR 1,500.00 | *Transaction of INR 1500.0 at pradee ac x3221 dt 14* |
| 546 | UNKNOWN | INR 1,150.00 | *HDFC Bank confirms a transaction of Rs.1150.00 from SUNDAR SONNIA RAMAMURTHY to HDFC Bank A/C *3221.* |

## 4. Direction Detection Validation

* **Direction Accuracy %**: 98.73% (Target: >= 90%)

## 5. Refund Detection Validation

* **Refund Count**: 4
* **Refund Accuracy %**: 100.00%

## 6. Transfer Classification Validation

Verified **4** internal account transfers correctly classified under Transfer (INTERNAL_TRANSFER) with net cashflow unaffected.

| Signal ID | Amount | Leg Direction | Summary |
| --- | --- | --- | --- |
| 571 | INR 3,000.00 | INTERNAL_TRANSFER | *Transaction of INR 3000.0 at pradee ac x3221 dt 09* |
| 547 | INR 1,500.00 | INTERNAL_TRANSFER | *Transaction of INR 1500.0 at pradee ac x3221 dt 14* |
| 445 | INR 20,000.00 | INTERNAL_TRANSFER | *Transaction of INR 20000.0 at pradee ac x3221 dt 08* |
| 218 | INR 58,000.00 | INTERNAL_TRANSFER | *Transaction of INR 58000.0 at pradee ac x3221 dt 12* |

## 7. Recurring Payment Detection

Detected **5** recurring transaction candidates (Insurance/EMI/CC Payment):

| Signal ID | Amount | Category | Summary |
| --- | --- | --- | --- |
| 386 | INR 909.00 | INSURANCE_PAYMENT | *Receives an INSURANCE transaction amount of Rs.909.00 from HDFC Bank via SMS.* |
| 344 | INR 555.00 | INCOME_OTHER | *Received confirmation on the settlement of a claim and update about policy details.* |
| 274 | INR 56,409.00 | EXPENSE_UNCLASSIFIED | *Transaction of INR 56409.0 at emi* |
| 142 | INR 489.00 | EXPENSE_UNCLASSIFIED | *UPI Mandate with debit to Google Play and credit from HDFC Bank.* |
| 11 | INR 1,000.00 | INSURANCE_PAYMENT | *Personal Loan facility enabled for the customer at HDFC Bank.* |
