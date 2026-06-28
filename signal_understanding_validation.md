# Signal Understanding Agent: Validation Report

This report evaluates the performance, accuracy, and operational efficiency of the newly implemented **SignalUnderstandingAgent** in shadow mode against the legacy **SignalProcessor** pipeline.

## 1. Executive Summary

| Metric | Value |
| :--- | :--- |
| **Total Qualified Signals Processed** | 100 |
| **Deterministic (RULE_ENGINE) Count** | 76 (76.0%) |
| **LLM Inference Count** | 24 (24.0%) |
| **Average Understanding Confidence** | 0.96 |
| **Legacy Pipeline Alignment Match** | 86 / 100 (86.0%) |

> [!NOTE]
> The deterministic path successfully processed **76.0%** of qualified incoming signals, achieving our target optimization goal of bypassing LLM calls for 70-80% of standard SMS traffic.

---

## 2. Path Distribution

* **RULE_ENGINE**: 76 signals matched known deterministic banking, utility, insurance, and booking text rules.
* **LLM**: 24 signals required deep semantic intent mapping using Qwen local model inference.

---

## 3. Cognitive Categorization

### Class Taxonomy Distribution
* **FINANCIAL**: 81
* **INFORMATION**: 22
* **ACTION**: 18
* **ALERT**: 6
* **MEMORY**: 1

### Domain Distribution
* **FINANCE**: 80
* **INSURANCE**: 18
* **TRAVEL**: 5
* **FAMILY**: 1
* **MEDICAL**: 5
* **GENERAL**: 1
* **EDUCATION**: 1

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
  "summary": "Received INR 2,000.00 in HDFC Bank A/c xx3221 with an outstanding balance of INR 2,269.27.",
  "confidence": 0.9,
  "reason": "The transaction details indicate a financial movement in the recipient's account, requiring an immediate action.",
  "entities": {
    "people": [
      "PRADEEP"
    ],
    "organizations": [],
    "merchants": [],
    "monetary_value": {
      "amount": 2000.0,
      "currency": "INR"
    },
    "deadlines": [],
    "appointments": [],
    "locations": [],
    "travel_bookings": {},
    "bills": {
      "amount": 2000.0,
      "currency": "INR",
      "balance": 2269.27
    },
    "insurance_policies": {},
    "medical_events": {}
  },
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
We observed 14 classification variations:
* Msg: "Insurance renewal alert from TX-CVRFOX-S" | Legacy: `INSURANCE` | New Classes: `['INFORMATION', 'ACTION']`
* Msg: "Bill payment reminder from JM-HDFCBK-S" | Legacy: `FINANCIAL` | New Classes: `['INFORMATION', 'ACTION', 'ALERT']`
* Msg: "Received confirmation on claim settlement and updated balance, prompting follow-up feedback." | Legacy: `INSURANCE` | New Classes: `['ACTION', 'INFORMATION', 'ALERT']`
* Msg: "Insurance renewal alert from AD-UIICHO-S" | Legacy: `INSURANCE` | New Classes: `['INFORMATION', 'ACTION']`
* Msg: "Insurer confirms claim settlement for a policy, indicating money has moved and the balance is updated." | Legacy: `INSURANCE` | New Classes: `['ACTION', 'INFORMATION']`

---

## 6. Gaps & Next Steps
- **Domain Refinements**: Tune the LLM prompt to align `domains` consistently on edge-case chats.
- **Rules Sync**: Sync the rules engine keywords dynamically when user updates overriding mapping preferences.
