# Phase 1B Lock Baseline — Source Collectors

This document defines the baseline file locks and checksums for the validated and working configurations in Phase 1B.

---

## 1. Locked Source Files

| Component File | MD5 Checksum | Status |
|---|---|---|
| `src/agents/consumer/agent.py` | `9d3d0d6f79450da2801efd6a3c0c34fe` | LOCKED |
| `src/agents/consumer/orchestrator.py` | `f406fe40bcabf06ea2aae72ef92e8786` | LOCKED |
| `src/agents/consumer/collectors/bank_statement_collector.py` | `54b309718c0e867c838dd4710953a782` | LOCKED |
| `src/agents/consumer/collectors/gpay_collector.py` | `d5f6531f008496b3e58169a938ec326b` | LOCKED |
| `src/agents/consumer/collectors/sms_collector.py` | `2c6c835e058007a7a7a21254e0e46609` | LOCKED |
| `src/agents/consumer/collectors/whatsapp_collector.py` | `45ceac071b187c31786e74345178dc79` | LOCKED |
| `src/agents/consumer/parsers/pdf_parser.py` | `15a7fa6b4267fe1e036ebba682121ca5` | LOCKED |
| `src/agents/consumer/parsers/sms_parser.py` | `0ad40ba9b96a1b515659ff74b939b8e6` | LOCKED |
| `src/agents/consumer/parsers/whatsapp_parser.py` | `a13930675600b2c08a7a96c9d91d34d5` | LOCKED |
| `src/agents/consumer/normalizers/financial_normalizer.py` | `6a576de87aa2c99b5839799fad02efe0` | LOCKED |
| `src/agents/consumer/normalizers/sms_normalizer.py` | `a0dd72b1bb880cf370ec8ab3b26e113f` | LOCKED |
| `src/agents/consumer/normalizers/whatsapp_normalizer.py` | `f65b56d7fbe919c73183dcde90eff7a4` | LOCKED |

---

## 2. Validation Suite Lock

* File: [test_source_collectors.py](file:///home/prad/petprojects/ai/jarvis/tests/test_source_collectors.py)
* Test Suite DTD:
  1. `test_1_whatsapp_ingestion`
  2. `test_2_sms_ingestion`
  3. `test_3_gpay_ingestion`
  4. `test_4_bank_statement_ingestion`
  5. `test_5_mixed_batch`
