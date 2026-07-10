# SUA Shadow Validation Report

Generated at: 2026-07-10T04:10:12.060674+00:00
Active Model: qwen2.5:1.5b
Heuristics Variant: Fallback Rule Heuristics

## Shadow Alignment Metrics

- **Total Signals Evaluated**: 110
- **LLM vs Heuristic Match Rate**: 90.91%
- **Heuristics Disagreement Count**: 10

## Disagreement Log

Log of signals where the active LLM classifier disagreed with the heuristics fallback classifier:

| Message | Expected Type | LLM Actual Type | Heuristic Fallback Type | Processing Path |
|---|---|---|---|---|
| Received from Nagarajan A | FINANCIAL | ACTION | FINANCIAL | llm |
| Let me see Pradeep ,pre prod week is going on I’ll update in... | NOISE | ACTION | NOISE | llm |
| 348959 is the OTP for Trxn. of INR 244.00 at FLIPKART I with... | NOISE | NOISE | FINANCIAL | fallback |
| Received from kalai chelvi | FINANCIAL | ACTION | FINANCIAL | llm |
| Wil try the web url | NOISE | ACTION | NOISE | llm |
| Got the link | NOISE | ACTION | NOISE | llm |
| Received from Shobana Kumari | FINANCIAL | ACTION | FINANCIAL | llm |
| Received from NAGARAJAN A | FINANCIAL | ACTION | FINANCIAL | llm |
| Done , Pradeep! | NOISE | ACTION | NOISE | llm |
| Done , Pradeep! | NOISE | ACTION | NOISE | llm |
