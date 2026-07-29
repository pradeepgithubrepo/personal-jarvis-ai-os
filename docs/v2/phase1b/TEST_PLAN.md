# Phase 1B Test Plan — Source Collectors

This document defines the automated validation scenarios, inputs, and database assertions used to verify that the Phase 1B Source Collectors run correctly.

---

## 1. Test Dataset Locations

The test dataset is placed in subdirectories of the `jarvis-signals` storage bucket:
* **WhatsApp exports:** `incoming/whatsapp/`
* **SMS exports:** `incoming/sms/`
* **GPay PDF statements:** `incoming/gpay/`
* **Bank PDF statements:** `incoming/statements/`

---

## 2. Validation Scenarios

### Test 1: WhatsApp Ingestion
* **Goal:** Verify that raw WhatsApp exports are parsed and normalized to the Unified Signal Schema.
* **Checks:**
  * Status: `SUCCESS`
  * Message event timestamp preserved.
  * Chat name and attachment indicators are populated in metadata.
  * File is moved to `archive/whatsapp/`.

### Test 2: SMS Ingestion
* **Goal:** Verify that SMS inbox exports are ingested and normalized.
* **Checks:**
  * Message body and sender ID populated.
  * Preserves historical timestamps.
  * File is moved to `archive/sms/`.

### Test 3: GPay Ingestion
* **Goal:** Verify GPay statement PDF layout parsing.
* **Checks:**
  * GPay transaction details, dates, transaction type, amounts, UPI references, and counterparties are extracted.
  * Stores fields under `metadata` using the Financial Transaction Schema.
  * File is moved to `archive/gpay/`.

### Test 4: Bank Statement Ingestion
* **Goal:** Verify SBI and HDFC bank statement PDF layout parsing.
* **Checks:**
  * Matches dates, transaction descriptions, debits, credits, reference IDs, and contact_7nces.
  * Normalizes and inserts transactions to `mobile_signals`.
  * File is moved to `archive/statements/`.

### Test 5: Mixed Ingestion Batch
* **Goal:** Verify orchestrator mixed-batch execution.
* **Checks:**
  * Runs all four collectors in a single pipeline execution.
  * Ensures all files across all subfolders are processed and archived.
  * Metrics are fully aggregated.

---

## 3. Running Automated Tests

Run the following command to execute the test suite:
```bash
/home/user/petprojects/ai/jarvis/.venv/bin/python -m unittest tests/test_source_collectors.py
```
