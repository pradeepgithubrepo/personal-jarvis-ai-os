# FYI Agent Validation Report

## 1. Input Summary

* **Signals Evaluated**: 264
* **FYI Candidates**: 226

## 2. FYI Generation Summary

* **FYIs Generated**: 226
* **FYIs Suppressed**: 184
* **Net FYIs**: 42

## 3. Category Distribution

* **FINANCIAL**: 15
* **PERSONAL**: 16
* **TRAVEL**: 3
* **HEALTH**: 1
* **FAMILY**: 7

## 4. Importance Distribution

* **MEDIUM**: 31
* **HIGH**: 11

## 5. Deduplication Audit

* **Deduplication Accuracy %**: 100.00% (Target: >= 95%)

## 6. Todo Leakage Audit

* **Action Leakage count**: 0
* **Todo Leakage rate**: 0.00% (Target: 0%)

## 7. Fact Leakage Audit

* **Fact Leakage count**: 0
* **Fact Leakage %**: 0.00% (Target: < 5%)

## 8. Hallucination Audit

* **Hallucination Rate %**: 0.00% (Target: 0%)

## 9. 25 Sample FYIs

| Source ID | Title | Category | Importance | Summary |
| --- | --- | --- | --- | --- |
| df011430-b00b-5b6d-9067-3aa1f5ce81da | Pradeep's call requesting a meeting, accompanied by family update. | FAMILY | HIGH | *The signal is general in nature and does* |
| e1ec341b-0d03-5385-bafd-00b7bf4a0ec7 | UPI top-up successful and refund information received. | FINANCIAL | HIGH | *The message is about a delivery update, * |
| dbb5a051-07a7-53c9-93a4-f599d7f666aa | Received a financial transaction from HDFC Bank, Rs. 1536.00. | FINANCIAL | MEDIUM | *The message indicates a confirmed debit * |
| 6fd4688c-6fa7-5fdb-adf6-de8dbabf1a39 | Amex: Stay alert! Know more about preventing money mule scams. | PERSONAL | MEDIUM | *The message is not specifically related * |
| cb2889a7-256a-55e5-86eb-dac0e97027c2 | Congratulations on setting a PIN using HDFC Bank Mobile App. Follow up action is provided. | PERSONAL | MEDIUM | *The message does not contain family-rela* |
| 4a7c32a5-4183-5614-b898-dba4c9aface3 | Activation of Pockets by ICICI Bank for Pradeep. | PERSONAL | MEDIUM | *The message is a general notification an* |
| 12e4c1e2-fbcf-5efe-9dfc-cc4985e1d499 | Transaction of INR 938.0 at 5676791 | PERSONAL | MEDIUM | *Deterministic match of financial transac* |
| 1a9a1ea9-5ca8-56b4-8931-ffe04daded54 | Applishing bill notification for Rs.291.35 from Apollo Pharmacy. | FINANCIAL | MEDIUM | *The message indicates an incoming financ* |
| 95d40a39-61a1-5e95-8297-096122674e3b | Gift Card Update: Payment confirmed, balance updated. | FINANCIAL | MEDIUM | *This message indicates a financial trans* |
| ef202102-689e-5e9d-a843-40985a319a19 | ICICI Bank prepaid card services will be unavailable due to scheduled maintenance. | FINANCIAL | MEDIUM | *The message confirms the prepayment card* |
| 256bc6ac-d43f-5721-a06e-574f37e74b4d | Received a notification about a policy issued by HDFC ERGO and an insurance policy transfer. | PERSONAL | MEDIUM | *The message contains details related to * |
| 1b50a179-f2be-5054-953b-d749198c7692 | Transaction of INR 350.0 at sbi cards and paymen | FINANCIAL | MEDIUM | *Deterministic match of financial transac* |
| 3236385f-b158-5c72-925f-c62324bc1f70 | Family notification about school update involving children. | FAMILY | HIGH | *The message is related to a family conte* |
| 7ac7c095-900a-593e-aa12-e5fbea5bb7dd | Daily Badminton Update message on a government holiday, asking for school day. | FAMILY | HIGH | *Message is about an upcoming badminton p* |
| 69d12581-b45d-5dfe-aee1-0ea54e4d8149 | Family update with positive emoticon, no specific domain or classes identified. | PERSONAL | MEDIUM | *The message contains a positive sentimen* |
| 2e2b7eb0-6b93-5ed8-a370-c6ae07b7d508 | ICICI Bank fetched BZ-CKYCR-S record for PRADEEP PANNEERSELVAM, reference 40038911417659 on May 26, 2026. | FINANCIAL | MEDIUM | *This is a financial transaction related * |
| a12ea2a6-1d38-51d9-997c-c17af9253a92 | Receipt for online payment confirmation of Rs 930, order no. 2-005721514762. | PERSONAL | MEDIUM | *This is a financial transaction related * |
| 50e8a32f-6742-5526-9152-6622263b0210 | Financial alert for a 2-year warranty on Vidiem AIR Plus 3 Burner Gas Stove, confirming a payment has moved. | PERSONAL | MEDIUM | *The message contains financial informati* |
| 4d2b3db9-c06b-5ecb-9dfe-0f642b06046d | Child is spending excessive time on YouTube, not listening to content. Parental intervention recommended. | FAMILY | HIGH | *The message indicates that the child is * |
| a2dde6b0-24df-52ab-88e6-5e6992da58a7 | UPI Mandate with debit to Google Play and credit from HDFC Bank. | FINANCIAL | MEDIUM | *The message indicates a transaction wher* |
| c89451ad-c88b-5965-938b-fe1a92203594 | Axis Bank Credit Card update: Change usage and transaction limits. Contact Axis Bank for further details. | PERSONAL | MEDIUM | *The message indicates an update to the c* |
| 24273c22-3622-5919-ac06-6233f7066fc0 | Payment of INR 352.82 received towards Axis Bank Credit Card. | FINANCIAL | MEDIUM | *The message clearly indicates a financia* |
| 3ac84e54-0c9f-5d6d-88ae-52d2ed816a87 | HDFC Bank transfer for INR 2,35,000.00 from account XXXX-XXX to account xxxxxxxxxx3724 via IMPS. | PERSONAL | MEDIUM | *The message explicitly mentions a financ* |
| c3c9b153-23b4-5940-ac7d-fe35dfec1cea | Family confirmation of happy mood | PERSONAL | MEDIUM | *The message indicates a positive emotion* |
| 45f11c85-41e0-50d0-8652-d18d2cd56b5b | School update: Friday is a holiday due to Muharram, thanks. | FAMILY | HIGH | *The message mentions the next day's scho* |

## 10. Final Verdict

### **FINAL VERDICT: FYI_AGENT_LOCKED**
