# SUA Shadow Validation Report

Generated at: 2026-07-13T03:29:27.426819+00:00
Active Model: qwen2.5:1.5b
Heuristics Variant: Fallback Rule Heuristics

## Shadow Alignment Metrics

- **Total Signals Evaluated**: 110
- **LLM vs Heuristic Match Rate**: 99.09%
- **Heuristics Disagreement Count**: 1

## Disagreement Log

Log of signals where the active LLM classifier disagreed with the heuristics fallback classifier:

| Message | Expected Type | LLM Actual Type | Heuristic Fallback Type | Processing Path |
|---|---|---|---|---|
| 348959 is the OTP for Trxn. of INR 244.00 at FLIPKART I with... | NOISE | NOISE | FINANCIAL | fallback |
