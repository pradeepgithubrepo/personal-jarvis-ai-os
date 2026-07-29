# SMS & WHATSAPP UNSTRUCTURED MESSAGE AUDIT REPORT
**Jarvis V2 Pipeline Rebuild — Stage 2 (Understanding Boundary)**

---

## 1. Executive Summary

This audit evaluates the classification and contract generation performance for all **unstructured signals** (SMS and WhatsApp messages) during the Jarvis V2 backfill execution. 

Because unstructured signals lack the physical payload metadata present in structured sources (such as GPay statements), they were routed through the **Signal Understanding Agent (SUA) processing loop**. Due to local CPU hardware constraints during the backfill, these signals transitioned to the **SUA Deterministic Fallback Parser** (`_fallback_understand`). This fallback parser serves as a safety baseline when LLM inference is disabled or times out.

---

## 2. Volumetrics & Classifications

Of the **840 signals** successfully ingested into `understood_signals`, **515 signals** were unstructured and processed via the fallback pipeline.

### 2.1 Source Distribution
| Source Channel | Qualified Ingest Count | Processing Path |
|---|---|---|
| **SMS** | 486 | Fallback Heuristic |
| **WhatsApp** | 29 | Fallback Heuristic |
| **Total** | **515** | |

### 2.2 Classified Target Type Breakdown
The deterministic fallback parser classified the 515 unstructured signals into three semantic categories:

```text
       Total Unstructured Signals (515)
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  [ FINANCIAL ]   [ ACTION ]     [ NOISE ]
    417 (81%)      29 (5.6%)     69 (13.4%)
```

* **FINANCIAL (417 records)**: Active transaction alerts, debit/credit notifications, card spend logs matching financial keyword lists.
* **ACTION (29 records)**: Direct task requests, reminders, and checklists containing action verbs.
* **NOISE (69 records)**: General chat updates, policy notifications, and promotional messages that lack transactional or actionable intent.

---

## 3. Heuristic Engine Rules

The fallback parser uses strict string matching and regular expressions to parse unstructured text:

### 3.1 Financial Rules
* **Trigger Keywords**: `credited`, `debited`, `spent`, `spent on`, `card ending`, `upi`, `emi`, `salary`, `payment`, `bank`, `paid to`, `received from`, `transferred`, `txn`
* **Amount Regex Extraction**: `(?:rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)`
* **Transaction Type**:
  * Classified as `CREDIT` if message contains: `credited`, `received`
  * Classified as `DEBIT` if message contains: `debited`, `spent`, `paid`
  * Defaulted to `UNKNOWN` otherwise.

### 3.2 Action Rules
* **Trigger Keywords**: `remind`, `todo`, `todo:`, `task:`, `action:`, `buy`, `call `, `please`, `can you`, `could you`, `share`, `send`, `give`
* **Contract Extraction**: Maps the entire raw message as `task_name` and assigns it to `unknown` with a null `due_date`.

---

## 4. Case Studies & Real Examples

### 4.1 WhatsApp Action Item (Successfully Captured)
* **Sender**: `WhatsApp: Shobana`
* **Message**: *"Purifier person don't pick up the call so register complaint"*
* **Target Classification**: `ACTION` (Trigger keyword: `call `)
* **Contract Output**:
```json
{
  "task_name": "Purifier person don't pick up the call so register complaint",
  "assignee": "unknown",
  "due_date": null,
  "requires_action": true,
  "memory_candidate": true
}
```
* **Audit Notes**: Correctly classified and converted into a standard Todo Agent format.

### 4.2 HDFC Bank Credit (Successfully Captured)
* **Sender**: `JM-HDFCBK-S`
* **Message**: *"Received! INR 2,000.00 in HDFC Bank A/c xx3221 On 27-06-26 For IMPS -PRADEEP P- 617813872256"*
* **Target Classification**: `FINANCIAL` (Trigger keyword: `bank`)
* **Contract Output**:
```json
{
  "amount": 2000.0,
  "currency": "INR",
  "transaction_type": "CREDIT",
  "payment_channel": "UNKNOWN",
  "merchant": null
}
```
* **Audit Notes**: The regex parser successfully stripped formatting commas to extract the numerical value `2000.0` and correctly mapped the transaction type to `CREDIT` based on the keyword `"Received!"`.

### 4.3 Axis Bank Survey (Noise Handled as Financial Candidate)
* **Sender**: `AX-AXISBK-S`
* **Message**: *"Axis Bank is open to hear your feedback on your recent email interaction. Click https://ccm.axis.bank.in/AXISBK/sVpNCJ1v to start..."*
* **Target Classification**: `FINANCIAL` (Trigger keyword: `bank`)
* **Contract Output**:
```json
{
  "amount": null,
  "currency": null,
  "transaction_type": "UNKNOWN",
  "payment_channel": "UNKNOWN",
  "merchant": null
}
```
* **Audit Notes**: Because the message contained the word `"Bank"`, it triggered the financial keyword heuristic. However, the contract generated `null` for amount and `UNKNOWN` for type, indicating no financial action should be taken by the downstream ledger.

### 4.4 The "Received" Edge Case (Heuristic Miss)
* **Sender**: `AX-UIICHO-S`
* **Message**: *"Dear Customer, Received INR 909 Receipt No 11302060026156896167 on 22/05/2026. Plz submit..."*
* **Target Classification**: `NOISE`
* **Contract Output**: `{}`
* **Audit Notes**: Although this message contains transaction details, the financial keywords list specifically checks for the composite phrase `"received from"` instead of the single word `"received"` to avoid false positives in general conversation. Consequently, it fell back to `NOISE`.

---

## 5. Summary & Key Recommendations

1. **Heuristic Baseline Safety**: The fallback parser operates as a highly safe baseline. It prevents pipeline crashes when the LLM is unavailable and processes records in microseconds.
2. **LLM Semantic Advantages**: When running the active system in production (with the 30-second timeout restored), the local Ollama LLM will successfully resolve complex sentences (like the *"Received"* edge case in Section 4.4) by reasoning about the context instead of depending on exact keyword matches.
3. **Keyword Refinement Suggestion**: We should consider adding `"received"` and `"receipt"` directly to the financial keyword fallback rules to improve credit capture rates when running in offline/fallback mode.
