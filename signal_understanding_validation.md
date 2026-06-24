# Signal Understanding Agent: Validation Report

This report evaluates the performance, accuracy, and operational efficiency of the newly implemented **SignalUnderstandingAgent** in shadow mode against the legacy **SignalProcessor** pipeline.

## 1. Executive Summary

| Metric | Value |
| :--- | :--- |
| **Total Qualified Signals Processed** | 100 |
| **Deterministic (RULE_ENGINE) Count** | 71 (71.0%) |
| **LLM Inference Count** | 29 (29.0%) |
| **Average Understanding Confidence** | 0.98 |
| **Legacy Pipeline Alignment Match** | 88 / 100 (88.0%) |

> [!NOTE]
> The deterministic path successfully processed **71.0%** of qualified incoming signals, achieving our target optimization goal of bypassing LLM calls for 70-80% of standard SMS traffic.

---

## 2. Path Distribution

* **RULE_ENGINE**: 71 signals matched known deterministic banking, utility, insurance, and booking text rules.
* **LLM**: 29 signals required deep semantic intent mapping using Qwen local model inference.

---

## 3. Cognitive Categorization

### Class Taxonomy Distribution
* **FINANCIAL**: 83
* **INFORMATION**: 18
* **ACTION**: 12
* **ALERT**: 2
* **MEMORY**: 2

### Domain Distribution
* **FINANCE**: 85
* **INSURANCE**: 10
* **TRAVEL**: 4
* **MEDICAL**: 2
* **WORK**: 1
* **EDUCATION**: 1
* **FAMILY**: 1

---

## 4. Sample Understanding Contracts

```carousel
```json
{
  "signal_id": "14",
  "signal_type": "financial_transaction",
  "classes": [
    "FINANCIAL"
  ],
  "domains": [
    "FINANCE"
  ],
  "importance": "LOW",
  "summary": "Transaction of INR 2000.0 at VA-SBIPSG-T",
  "confidence": 1.0,
  "reason": "Deterministic match of financial transaction keywords",
  "entities": {
    "people": [],
    "organizations": [
      "VA-SBIPSG-T"
    ],
    "merchants": [
      "VA-SBIPSG-T"
    ],
    "monetary_value": {
      "amount": 2000.0,
      "currency": "INR"
    },
    "deadlines": [],
    "appointments": [],
    "locations": [],
    "travel_bookings": {},
    "bills": {},
    "insurance_policies": {},
    "medical_events": {}
  },
  "routes": [
    "FinancialAgent"
  ],
  "raw_context": {
    "source": "sms",
    "sender": "VA-SBIPSG-T",
    "timestamp": "2026-06-20T00:40:18.768000",
    "processing_path": "RULE_ENGINE",
    "llm_model_used": "none"
  }
}
```
<!-- slide -->
```json
{
  "signal_type": "financial_transaction",
  "classes": [
    "FINANCIAL"
  ],
  "domains": [
    "FINANCE"
  ],
  "importance": "HIGH",
  "summary": "Received INR 2,000.00 for HDFC Bank A/c xx3221 on 20-06-26 and current balance is INR 2,269.27.",
  "confidence": 0.95,
  "reason": "The message includes a financial transaction in an Indian bank account with a specific identification number (INR 2,000.00 for HDFC Bank A/c xx3221), indicating high importance and priority over other messages.",
  "entities": {},
  "routes": [
    "FinancialAgent"
  ],
  "signal_id": "15",
  "raw_context": {
    "source": "sms",
    "sender": "JM-HDFCBK-S",
    "timestamp": "2026-06-20T00:40:12.023000",
    "processing_path": "LLM",
    "llm_model_used": "qwen2.5:1.5b"
  }
}
```
<!-- slide -->
```json
{
  "signal_id": "18",
  "signal_type": "financial_transaction",
  "classes": [
    "FINANCIAL"
  ],
  "domains": [
    "FINANCE"
  ],
  "importance": "LOW",
  "summary": "Transaction of INR 293.0 at VM-SBICRD-S",
  "confidence": 1.0,
  "reason": "Deterministic match of financial transaction keywords",
  "entities": {
    "people": [],
    "organizations": [
      "VM-SBICRD-S"
    ],
    "merchants": [
      "VM-SBICRD-S"
    ],
    "monetary_value": {
      "amount": 293.0,
      "currency": "INR"
    },
    "deadlines": [],
    "appointments": [],
    "locations": [],
    "travel_bookings": {},
    "bills": {},
    "insurance_policies": {},
    "medical_events": {}
  },
  "routes": [
    "FinancialAgent"
  ],
  "raw_context": {
    "source": "sms",
    "sender": "VM-SBICRD-S",
    "timestamp": "2026-06-19T01:08:07.826000",
    "processing_path": "RULE_ENGINE",
    "llm_model_used": "none"
  }
}
```
```

---

## 5. Comparison Against Legacy SignalProcessor

### Observed Improvements
1. **Low Latency / Lower Compute**: Deterministic pipeline intercepts standard debit messages instantly without starting Ollama/Local LLM process, ensuring rapid ingestion.
2. **Decoupled Architecture**: Downstream database models are untouched. Lineage is tracked via `raw_signal_id` and `qualified_signal_id` in `understood_signals`.
3. **Domain Richness**: Introducing specific domains like `FAMILY`, `MEDICAL`, and `TRAVEL` enables downstream agents to store metadata with cleaner context mapping than the old broad categories.

### Mismatches & False Classifications
We observed 12 classification variations:
* Msg: "Alert: Rs. 7,791 refunded by Flipkart Internet PR on HDFC Bank Credit Card." | Legacy: `FINANCIAL` | New Classes: `['INFORMATION']`
* Msg: "SBI Bill Alert: Rs.3141.02 is due on 01-Jul-2026, payment required via HDFC Net/Mobile Banking." | Legacy: `FINANCIAL` | New Classes: `['INFORMATION', 'ALERT']`
* Msg: "Received INR 50,000.00 in HDFC Bank account A/c xx3221." | Legacy: `FINANCIAL` | New Classes: `['INFORMATION', 'ACTION']`
* Msg: "Rs.930.00 transferred from HDFC Bank A/C *3221 to Amazon Pay on 30/05/26, Ref #615061323381." | Legacy: `FINANCIAL` | New Classes: `['INFORMATION']`
* Msg: "Your bike insurance policy has been updated, and you're being reminded to download the new document." | Legacy: `INSURANCE` | New Classes: `['INFORMATION']`

---

## 6. Gaps & Next Steps
- **Domain Refinements**: Tune the LLM prompt to align `domains` consistently on edge-case chats.
- **Rules Sync**: Sync the rules engine keywords dynamically when user updates overriding mapping preferences.
