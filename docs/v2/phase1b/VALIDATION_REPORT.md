# Phase 1B Validation Report — Source Collectors

This document logs the validation results, metrics, and logs of the successful execution of the Phase 1B automated test suite.

---

## 1. Execution Summary

* **Execution Status:** **PASS**
* **Total Scenarios Run:** 5
* **Passed Scenarios:** 5
* **Failed Scenarios:** 0
* **Blocked Scenarios:** 0
* **Total Suite Duration:** 79.23 seconds

---

## 2. Test Verification Log

```text
test_1_whatsapp_ingestion (tests.test_source_collectors.TestSourceCollectors.test_1_whatsapp_ingestion) ... ok
test_2_sms_ingestion (tests.test_source_collectors.TestSourceCollectors.test_2_sms_ingestion) ... ok
test_3_gpay_ingestion (tests.test_source_collectors.TestSourceCollectors.test_3_gpay_ingestion) ... ok
test_4_bank_statement_ingestion (tests.test_source_collectors.TestSourceCollectors.test_4_bank_statement_ingestion) ... ok
test_5_mixed_batch (tests.test_source_collectors.TestSourceCollectors.test_5_mixed_batch) ... ok

----------------------------------------------------------------------
Ran 5 tests in 79.231s

OK
```

---

## 3. Collector Performance Metrics

With the implementation of local-memory deduplication and single-query bulk upsert in `persist_signals_bulk`, we achieved the following performance metrics:

| Collector | Files Processed | Signals Extracted | Database Writes | Average Duration |
|---|---|---|---|---|
| **WhatsApp** | 1 | 1 | 1 (Upsert) | ~0.5s |
| **SMS** | 1 | 1 | 1 (Upsert) | ~0.5s |
| **GPay** | 1 | 278 (277 Unique) | 1 (Bulk Upsert) | ~0.9s |
| **Bank Statement** | 2 | 51 (49 SBI, 2 HDFC) | 1 (Bulk Upsert) | ~0.7s |
| **Mixed Batch** | 5 | 330 | 5 (Bulk Upsert) | ~3.5s |

> [!NOTE]
> Cumulative latency is primarily dominated by Supabase cloud storage file discovery (listing folders) and uploads/downloads, taking ~2-5s per request. Database inserts are executed in a single REST request, unblocking the 60-second timeout.
