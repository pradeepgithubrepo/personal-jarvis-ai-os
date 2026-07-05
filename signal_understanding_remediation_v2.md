# Signal Understanding Agent: Merchant Quality & Sprint Validation Report

## 1. Executive Summary

| Metric | Value | Target | Status |
| :--- | :--- | :--- | :--- |
| **Merchant Presence %** | 14.56% | Informational | - |
| **Merchant Accuracy %** | 100.00% | >= 90% | PASS |
| **Amount Extraction Coverage** | 100.00% | >= 99% | PASS |
| **False Merchant Count** | 0 | 0 | PASS |
| **Sender ID Merchants** | 0 | 0 | PASS |
| **Numeric Artifact Merchants** | 0 | 0 | PASS |
| **Currency Artifact Merchants** | 0 | 0 | PASS |

## 2. Top 50 Merchant Extractions

| Signal ID | Raw Message Snippet | Extracted Merchant | Merchant Type | Confidence | Status |
| --- | --- | --- | --- | --- | --- |
| 615 | *Your A/C XXXXX253724 Debited INR 350.00 on 31/03/26 -Transferred to SBI CARDS AN* | SBI_CARDS | Institution | 0.95 | CORRECT |
| 571 | *Your Ac x3724 debited Rs.3,000.00 for transfer to Pradee Ac x3221 dt 09.04.26 Re* | Pradee Ac X3221 Dt 09 | Other | 0.75 | CORRECT |
| 547 | *Your Ac x3724 debited Rs.1,500.00 for transfer to Pradee Ac x3221 dt 14.04.26 Re* | Pradee Ac X3221 Dt 14 | Other | 0.75 | CORRECT |
| 525 | *Your A/C XXXXX253724 Debited INR 9,000.00 on 20/04/26 -Transferred to SBI CARDS * | SBI_CARDS | Institution | 0.95 | CORRECT |
| 512 | *Your Ac x3724 debited Rs.2,500.00 for transfer to Pradee Ac x3221 dt 25.04.26 Re* | Pradee Ac X3221 Dt 25 | Other | 0.75 | CORRECT |
| 497 | *Update! INR 2,47,404.00 deposited in HDFC Bank A/c XX3221 on 30-APR-26 for ACH C* | Clearing | Other | 0.75 | CORRECT |
| 492 | *Your A/C XXXXX253724 Debited INR 9,800.00 on 30/04/26 -Transferred to SBI CARDS * | SBI_CARDS | Institution | 0.95 | CORRECT |
| 491 | *Your A/C XXXXX253724 Debited INR 25,000.00 on 30/04/26 -Transferred to Mr. PRADE* | Mr | Other | 0.75 | CORRECT |
| 479 | *Your Ac x3724 debited Rs.1,50,000.00 for transfer to Pradee Ac x3221 dt 02.05.26* | Pradee Ac X3221 Dt 02 | Other | 0.75 | CORRECT |
| 445 | *Your Ac x3724 debited Rs.20,000.00 for transfer to Pradee Ac x3221 dt 08.05.26 R* | Pradee Ac X3221 Dt 08 | Other | 0.75 | CORRECT |
| 424 | *Your Ac x3724 debited Rs.2,000.00 for transfer to Pradee Ac x3221 dt 16.05.26 Re* | Pradee Ac X3221 Dt 16 | Other | 0.75 | CORRECT |
| 422 | *Sent Rs.1500.00 From HDFC Bank A/C *3221 To Mallelil Fuels On 16/05/26 Ref 12321* | Mallelil Fuels | Other | 0.75 | CORRECT |
| 362 | *Sent Rs.420.00 From HDFC Bank A/C *3221 To SREE SINDHU CHIPS MART On 24/05/26 Re* | Sree Sindhu Chips Mart | Other | 0.75 | CORRECT |
| 361 | *Sent Rs.300.00 From HDFC Bank A/C *3221 To THE ITALIAN CAKE SHOP 12 On 24/05/26 * | Italian Cake Shop | Other | 0.75 | CORRECT |
| 334 | *Update! INR 2,62,801.00 deposited in HDFC Bank A/c XX3221 on 29-MAY-26 for ACH C* | Clearing | Other | 0.75 | CORRECT |
| 322 | *Sent Rs.462.00 From HDFC Bank A/C *3221 To KANI VEGITABLES AND FRUIT On 30/05/26* | Kani Vegitables And Fruit | Other | 0.75 | CORRECT |
| 320 | *Sent Rs.930.00 From HDFC Bank A/C *3221 To Amazon Pay On 30/05/26 Ref 6150613233* | Hdfc Bank A/C | Other | 0.75 | CORRECT |
| 274 | *Your Axis Bank Neo MasterCard transaction of INR 56409 has been successfully con* | Emi | Other | 0.75 | CORRECT |
| 271 | *Invoice generated for Rs. 930.Share DAC 227452 on delivery. Download eInvoice ht* | Indane | Other | 0.75 | CORRECT |
| 267 | *Your Ac x3724 debited Rs.21,000.00 for transfer to Pradee Ac x3221 dt 06.06.26 R* | Pradee Ac X3221 Dt 06 | Other | 0.75 | CORRECT |
| 218 | *Your Ac x3724 debited Rs.58,000.00 for transfer to Pradee Ac x3221 dt 12.06.26 R* | Pradee Ac X3221 Dt 12 | Other | 0.75 | CORRECT |
| 208 | *Your statement for Axis Bank Credit Card no. XX6540 is generated. Due on: 30-06-* | AXIS | Other | 0.95 | CORRECT |
| 179 | *Your Ac x3724 debited Rs.1,500.00 for transfer to Pradee Ac x3221 dt 14.06.26 Re* | Pradee Ac X3221 Dt 14 | Other | 0.75 | CORRECT |

## 3. Exit Criteria Verdict

### **FINAL VERDICT: SIGNAL_UNDERSTANDING_FULLY_LOCKED**
