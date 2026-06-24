# Semantic Alignment Hardening Report (Module 3.1.1)

This report evaluates semantic classification alignment across 100 qualified signals, highlighting misclassifications, root causes, rule updates, and domain/class contract validation.

---

## 1. Alignment Summary

We analyzed **100 qualified signals** (covering SMS transaction records, WhatsApp group chats, utility alerts, insurance renewals, and mock signals).

* **Deterministic (RULE_ENGINE) Path**: 71% (71 signals)
* **LLM Path**: 29% (29 signals)
* **Legacy vs. New Contract Alignment**: 88% (88 matches out of 100)
* **Mismatches Detected**: 12% (12 signals)

---

## 2. Top Misclassifications & Root Cause Analysis

We identified three primary areas of semantic misalignment:

### A. Refunds Classified as Pure Information
* **Signal**: *"Alert! Rs. 7791 refunded by FLIPKART INTERNET PR on 15/JUN/2026 & adjusted against HDFC Bank Credit Card 7074..."*
* **Legacy Output**: `FINANCIAL`
* **Agent Output**: `["INFORMATION"]` (LLM Path)
* **Expected Output**: `["FINANCIAL", "INFORMATION"]`
* **Root Cause**: The LLM prioritized the text structure of the refund statement (e.g. notifications/alerts) as informational, failing to recognize that credit adjustments represent monetary inflows and must belong to `FINANCIAL`.

### B. Future Obligations (Bills Due) Classified as Financial Transactions
* **Signal**: *"New Bill Alert: Your SBI Card Bill 8707 of Rs.3141.02 is due on 01-Jul-2026..."*
* **Legacy Output**: `FINANCIAL`
* **Agent Output**: `["INFORMATION", "ALERT"]` (LLM Path)
* **Expected Output**: `["INFORMATION", "ACTION", "ALERT"]`
* **Root Cause**: The legacy pipeline treated bill due dates as immediate financial events. However, since no money has moved yet, it is not a transaction. The new agent correctly moved it out of `FINANCIAL` but missed the `ACTION` class required to trigger downstream payment todos.

### C. Insurance Renewals Classified as Financial Events
* **Signal**: *"Premium due for Policy No.316712630 is not yet received. Please pay premium online..."*
* **Legacy Output**: `INSURANCE`
* **Agent Output**: `["ACTION", "FINANCIAL"]` (RULE_ENGINE Path)
* **Expected Output**: `["INFORMATION", "ACTION"]`
* **Root Cause**: The deterministic rule for insurance matched the word "premium" and assumed a financial transaction. Like bills, insurance renewals are future obligations and do not represent transaction events until paid.

---

## 3. Semantic Alignment Matrix (Sample Review Table)

| Signal | Legacy Output | Understanding Agent Output | Expected Output | Recommended Rule Change | Final Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| *Rs.450 spent on Zomato* | `FINANCIAL` | `["FINANCIAL"]` | `["FINANCIAL"]` | None (deterministic matches) | `["FINANCIAL"]` |
| *Received INR 50,000.00* | `FINANCIAL` | `["INFORMATION", "ACTION"]` | `["FINANCIAL"]` | Classify received/deposit credits strictly under `FINANCIAL`. | `["FINANCIAL"]` |
| *Refund of Rs. 7,791 Flipkart* | `FINANCIAL` | `["INFORMATION"]` | `["FINANCIAL", "INFORMATION"]` | Add refund keywords to trigger credit inflows. | `["FINANCIAL", "INFORMATION"]` |
| *New Bill Alert: Due 01-Jul* | `FINANCIAL` | `["INFORMATION", "ALERT"]` | `["INFORMATION", "ACTION", "ALERT"]` | Force `ACTION` for outstanding due alerts. | `["INFORMATION", "ACTION", "ALERT"]` |
| *Renew policy before expiry* | `INSURANCE` | `["ACTION", "FINANCIAL"]` | `["INFORMATION", "ACTION"]` | Strip `FINANCIAL` tag from pre-payment renewal alerts. | `["INFORMATION", "ACTION"]` |
| *Circular: Exam schedule* | `FYI` | `["INFORMATION"]` | `["INFORMATION"]` | Confirm `INFORMATION` mapping. | `["INFORMATION"]` |
| *Submit science model by Wed* | `TODO` | `["INFORMATION", "ACTION"]` | `["INFORMATION", "ACTION"]` | Ensure homework contains both tags. | `["INFORMATION", "ACTION"]` |
| *Please pick up Charan from school*| `TODO` | `["ACTION"]` | `["ACTION"]` | Boost domain context to `FAMILY`. | `["ACTION"]` |
| *Appt at Apollo Clinic tomorrow* | `TODO` | `["ACTION"]` | `["INFORMATION", "ACTION"]` | Force both info circular & todo reminders. | `["INFORMATION", "ACTION"]` |

---

## 4. Domain & Class Validation

### Class Mappings
We confirm the semantic bounds of the five mandatory classes:
- **ACTION**: Active chores, submissions, pending payments (triggers `TodoAgent`).
- **FINANCIAL**: Direct debit/credit money movement transactions (triggers `FinancialAgent`).
- **INFORMATION**: Status events, circulars, confirmations (triggers `FyiAgent`).
- **MEMORY**: Facts, preferences, relationships (triggers `FactAgent`).
- **ALERT**: Critical notifications (security, disputes).

### Domain Mappings
We validated the eight domains. They map correctly across the dataset:
- `FAMILY`: WhatsApp messages from Shobana, parenting requests.
- `FINANCE`: Banking debits, credit alerts, refunds.
- `INSURANCE`: Policy renewals, claim notifications.
- `MEDICAL`: Phlebotomist assignments, clinic appointments.
- `TRAVEL`: Flight booking PNR confirmations, delivery status logs.
- `WORK`: Slack notifications, office messages.
- `EDUCATION`: Homework alerts, circular notifications.
- `GENERAL`: General recharges, telecom warnings.

---

## 5. Confidence Assignment Logic Review

### The Problem
Currently, deterministic rule-engine processing automatically outputs a confidence of `1.0`, while LLM output is hardcoded to a static `0.8` or `0.95`. This reflects **model confidence** (which is artificial) rather than **business confidence** (how safe it is to run automatically).

### Recommended Business Confidence Matrix
We propose calculating a hybrid `confidence` value dynamically based on:
1. **Source Reliability**: Direct transactional bank senders (e.g., `AD-HDFCBK`) get a `+0.1` boost. Unknown numeric WhatsApp senders get a `-0.1` penalty.
2. **Entity Completeness**: If `classes` contains `FINANCIAL` but `amount` is missing, apply a `-0.3` penalty.
3. **Parse Performance**: If the LLM output requires repair or regex cleaning, apply a `-0.15` penalty.

**Auto-Processing Threshold**: Only contracts with a final calculated confidence of `>= 0.85` will execute downstream automatically.

---

## 6. Internal Transfer Ownership Validation

The Signal Understanding Agent answers **"What happened?"** (e.g. *Account A debited; Account B credited*). It is a semantic mapping error to try to detect internal transfers at this stage because:
1. **Decoupled Isolation**: Determining if a debit and credit match requires cross-signal comparisons, time-window sliding scans, and account state checks. Doing this inside the Understanding Agent introduces statefulness and breaks its single-signal stateless contract.
2. **Financial Logic Belongs Downstream**: The future **Financial Agent** is the domain expert for spend aggregations, double-entry ledgers, and matching transfers. 

Thus, the Signal Understanding Agent will strictly emit `bank_transfer` types with the `FINANCIAL` class for both transfers, and let the downstream Financial Agent run matching logic.

---

## 7. Recommended Code Modifications (Do Not Implement Yet)

To resolve the misclassifications, we recommend updating the deterministic path in `services/signal_understanding_agent.py` as follows:

```python
# In _try_deterministic_path:
# 1. Update Insurance Renewal
if any(kw in msg_lower for kw in insurance_kws) and any(kw in msg_lower for kw in ["due", "renew", "expire", "expiry"]):
    return {
        "classes": ["INFORMATION", "ACTION"],  # Removed FINANCIAL
        "domains": ["INSURANCE"],
        ...
    }

# 2. Update Bill Reminder
if any(kw in msg_lower for kw in bill_kws) and any(kw in msg_lower for kw in ["due", "outstanding", "pending"]):
    return {
        "classes": ["INFORMATION", "ACTION", "ALERT"],  # Removed FINANCIAL
        "domains": ["FINANCE"],
        ...
    }
```
And refining the LLM prompt to strictly specify that **refunds** must include `FINANCIAL` and `INFORMATION` classes.
