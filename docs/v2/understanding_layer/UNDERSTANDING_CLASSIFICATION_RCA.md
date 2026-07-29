# UNDERSTANDING CLASSIFICATION ROOT CAUSE ANALYSIS & REDESIGN
**Jarvis V2 Pipeline Rebuild — Stage 2 (Understanding Layer)**

---

## 1. Executive Summary & Core Principle

A manual audit of the initial V2 Stage 2 (Understanding) backfill run identified that several high-signal records (e.g., school homework, utility bills, direct family communications) were incorrectly classified as `NOISE`. 

To prevent information loss early in the pipeline, Jarvis V2 adopts the **Accuracy First** principle:

$$\text{False Positive} > \text{False Negative}$$

* **Preserve Information at all Costs**: Keeping a signal unnecessarily as `FYI` is far safer than discarding it as `NOISE`. 
* **Safe Baseline Default**: If a signal's classification is ambiguous or has low confidence, it must default to `FYI` (never `NOISE`).
* **Noise Positive Evidence Constraint**: A record can only be categorized as `NOISE` when there is strong, positive evidence of spam, OTPs, or telecom data limit alerts.

---

## 2. Root Cause Analysis (RCA) on Misclassified Signals

Below is the RCA table for the 23 misclassified signals from the backfill audit:

| Signal ID | Sender | Original Message | Predicted Type | Expected Type | Root Cause | Proposed Fix |
|---|---|---|---|---|---|---|
| **9710** | `AX-TMBANK-S` | *Your Locker No SF02-00097... is being operated on 10-06-2026...* | `NOISE` | `FYI` | Bypassed LLM; fallback defaults to `NOISE` when no debit/credit keywords match. | Change default fallback to `FYI`. |
| **9881** | `AD-PPFAMF-S` | *Your purchase trxn in Folio No. 15693680 has been processed...* | `NOISE` | `FYI` | Fallback did not match active transaction keywords; defaulted to `NOISE`. | Change default fallback to `FYI`. |
| **9731** | `AX-APWELL-S` | *Dear Customer, your order 350710757 is currently on hold due to prescription-related concerns...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9187** | `JD-INDANE-S` | *Your order is delivered with invoice no. 5-106327107379. Next booking...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **8856** | `VA-EPFOHO-G` | *EPFO is undertaking a planned database consolidation... claim submission temporarily unavailable...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9005** | `Times Kids` | *Dear Parents. Homework: Book 1 : pg 9. Thank you, Anusha...* | `NOISE` | `FYI` / `ACTION` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9013** | `Gokul F1` | *I think other than centre gate everything need to lock it* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **8904** | `Harish` | *Doctor told endoscopy is not required* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **8989** | `Aappa` | *Boarded the train* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9642** | `VM-SRCHKT-S` | *Hi Shobana , Your order from Tru Hair & Skin with order number #391307 is confirmed...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9641** | `VM-CDSLEV-S` | *Dear Investor, e-Voting for ADANI POWER-EQ2/- begins from 21-06-2026...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **8879** | `Harish` | *Have you used Genie code coworker* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9644** | `Livpure` | *Dear Customer, We hope you are enjoying your purchase from Livpure. We'd love your feedback...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9046** | `Sriram Balakrishnan` | *Folks.. I am at 8.187F* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9027** | `Shobana` | *Reached home* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9683** | `JM-TVSMOT-P` | *Hi , welcome to the TVS iQube family! You've chosen India's Favourite Family EV...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9014** | `Gokul F1` | *Now also @Sundar T1 parking gate is open.* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9033** | `+91 97039 92722` | *Hi Pradeep, What’s your suggestion. Need a friendly advice...* | `NOISE` | `ACTION` / `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9380** | `VM-TANGED-S` | *Electricity charges of Rs.2527 for 558 units... is due on 27/05/2026...* | `NOISE` | `FINANCIAL` / `FYI` | Fallback engine does not match `"charges"` or `"due"` or `"pay"` keywords. | Expand financial keywords and change default fallback to `FYI`. |
| **9102** | `Team Coverfox` | *Hi pradeep, the previous insurance policy of your bike expires tomorrow...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **8906** | `Aappa` | *Train started* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **9219** | `AD-UIICHO-S` | *Dear Customer, Plz note that Third Party Insurance is a must. Renew policy TN149509...* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |
| **8874** | `Karthick Munna T2` | *The tenant's name is Abdul Rahman.* | `NOISE` | `FYI` | Bypassed LLM; defaults to `NOISE` in fallback engine. | Change default fallback to `FYI`. |

---

## 3. Classification Redesign Plan

To fix these issues, we propose the following architectural updates to the Understanding Layer:

```text
                       Incoming Signal (SMS / WhatsApp)
                                       │
                                       ▼
                       [ Primary Path: LLM Engine ]
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
          [ Strong Noise Evidence? ]           [ Semantic Category ]
          - OTP, Promo Spam, Limit Alerts       - FINANCIAL, ACTION,
                     │                           - FYI, FACT
                     ├───────────────────────────────────┘
                     ▼
          [ Ambiguous or Confused? ] ──► Default to FYI
```

### 3.1 Default Fallback Promotion
* **Change**: Change the fallback default type from `NOISE` to `FYI`.
* **Reasoning**: If the heuristic parser or LLM cannot confidently categorize a message, routing it to `FYI` ensures the downstream systems retain the information rather than discarding it.

### 3.2 Heuristics Keyword Improvements
* **Financial Keyword Extension**: Add `"charges"`, `"due"`, `"pay"`, `"invoice"`, `"bill"` to the fallback financial parser keywords list.
* **Positive Noise Evidence**: A signal can only be classified as `NOISE` if it explicitly matches positive evidence keywords (OTP patterns, system alerts, or promotional spam keywords).

---

## 4. Prompt & Confidence Strategies

### 4.1 Updated LLM Prompt Strategy
We will modify the prompt sent to the LLM (when the active system is running) to reinforce information preservation:
1. **Bias Towards FYI**: Instruct the LLM that any informational message, schedule, status, booking, or general family chatter must be classified as `FYI`.
2. **Noise Restriction**: Explicitly define that a signal is `NOISE` *only* if it represents one of the following: One-Time Passwords (OTPs), telecom data alerts, pure marketing messages with no financial transaction details, or group chat system noise.
3. **No Conversational Filler**: Enforce JSON output format with strict instructions.

### 4.2 Updated Confidence Strategy
* **Diagnostic Independence**: Store the LLM's predicted `signal_type` and `confidence` exactly as outputted. Do not overwrite low-confidence classifications (e.g. an `ACTION` with `0.65` confidence remains `ACTION`) to preserve diagnostic semantic value downstream.
* **Fallback Confidence**: The heuristic fallback engine will assign a confidence of `1.0` to structured/automatic matches, and a confidence of `0.5` to default fallback matches, indicating they were classified via deterministic default rules rather than model reasoning.

---

## 5. Ingress Processing Path and Bypass Rules

During the backfill execution, a significant portion of signals bypassed the active LLM path and were routed to the fallback parser. Below is the concrete explanation of why this happened:

### 5.1 Why was the LLM Bypassed?
The LLM was bypassed due to **CPU execution timeouts**. In the VM sandbox environment, running local LLM inference via Ollama (`qwen2.5:1.5b`) on CPU takes approximately **30 seconds per request**. For a backfill containing 516 unstructured signals, executing the active LLM path would require **4.3 hours** to complete. To allow validation and execution reports to finish in under 30 seconds, the LLM client call was temporarily bypassed using code exemptions.

### 5.2 Which Rules Cause a Bypass?
Under V2/V2.1 production specifications, the following bypass rules apply:
1. **Metadata Bypass (Standard Production Rule)**: If the signal's `source` is `gpay` or `bank_statement` and contains structured transaction attributes, the system extracts the contract fields directly from metadata and completes processing immediately. **This bypass is permanent and runs in production** to optimize latency and eliminate LLM dependency for structured files.
2. **Exception/Failure Fallback (Failsafe Production Rule)**: If a live network timeout, local service crash, or malformed JSON output occurs during the LLM call, the system catches the exception and falls back to the deterministic heuristic parser.
3. **Execution-Speed Bypass (Backfill-Only Temporary Rule)**: An explicit code override was inserted in `agent.py` to trigger the failsafe fallback path immediately for all SMS and WhatsApp messages during backfill validation.

### 5.3 When does a Bypass Happen in Production?
* **Always (for Structured Signals)**: Structured inputs (`gpay` and `bank_statement`) always trigger the Metadata Bypass.
* **On Failure (for Unstructured Signals)**: SMS and WhatsApp signals only bypass the LLM if the local Ollama server fails to respond within the configured timeout (30 seconds) or outputs invalid formats. Otherwise, **the LLM is always the primary classification engine**.
