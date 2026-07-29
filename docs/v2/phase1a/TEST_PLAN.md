# Phase 1A Test Plan — Consumption Infrastructure

This document outlines the testing strategy, scenarios, inputs, and validation checks used to verify that the Jarvis V2 Consumption Infrastructure works correctly under normal and error conditions.

---

## 1. Test Environment Setup

* **Database Schema:** `jarvis_insights_schemav1` (Active in Supabase)
* **Storage Bucket:** `jarvis-signals`
* **Incoming Path:** `incoming/`
* **Archive Path:** `archive/`
* **Test Orchestrator:** `/home/user/petprojects/ai/jarvis/.venv/bin/python -m unittest tests/test_consumer_agent.py`

---

## 2. Validation Test Scenarios

### Test 1: Single File Ingestion
* **Goal:** Verify that a standard JSON signal file with valid signals is downloaded, parsed, signals inserted, and file archived successfully.
* **Input:** Upload `test1_single.json` containing 2 signals to `incoming/`.
* **Execution:** Run the pipeline.
* **Expected Output:**
  * Status: `SUCCESS`
  * Files Found: 1, Files Processed: 1, Files Skipped: 0, Files Failed: 0
  * Signals Created: 2
  * `processed_files` gets 1 row with file SHA-256 hash.
  * File is moved from `incoming/` to `archive/`.

---

### Test 2: Idempotency (Duplicate File Skip)
* **Goal:** Verify that processing the exact same file content again does not duplicate work.
* **Input:** Upload another file with the exact same bytes as `test1_single.json` (e.g. `test2_dup.json`) to `incoming/` while its hash is already present in `processed_files`.
* **Execution:** Run the pipeline.
* **Expected Output:**
  * Status: `SUCCESS`
  * Files Found: 1, Files Processed: 0, Files Skipped: 1, Files Failed: 0
  * Signals Created: 0
  * Duplicate file is removed from `incoming/` folder.

---

### Test 3: Partial Failure (Broken JSON)
* **Goal:** Verify that a malformed JSON file does not crash the pipeline, but is logged as failed, and the run finishes as `PARTIAL_SUCCESS` if other files succeed.
* **Input:** Upload `test3_broken.json` (malformed JSON string) and a valid `test3_valid.json` containing 1 signal.
* **Execution:** Run the pipeline.
* **Expected Output:**
  * Status: `PARTIAL_SUCCESS`
  * Files Found: 2, Files Processed: 1, Files Skipped: 0, Files Failed: 1
  * Signals Created: 1
  * The broken file is moved to `failed/` directory to clear it from incoming.
  * The valid file is archived.

---

### Test 4: Supabase Unavailable
* **Goal:** Verify that when the database is unavailable, the pipeline records/logs the failure, exits with code `1`, and status is `FAILED`.
* **Input:** Provide an invalid `SUPABASE_URL` to the client.
* **Execution:** Run the pipeline.
* **Expected Output:**
  * Pipeline execution prints the crash error.
  * The runner exits with status code `1` (or status in metrics is set to `FAILED`).

---

### Test 5: Message-Level Deduplication (Agent Rerun)
* **Goal:** Verify that if the same signals are parsed from different files (or on agent rerun if files are manually re-introduced), the database UNIQUE constraint prevents duplicate `mobile_signals` entries.
* **Input:** Upload `test5_newfile.json` containing a signal with the exact same content and timestamp as a previously processed signal.
* **Execution:** Run the pipeline.
* **Expected Output:**
  * Status: `SUCCESS`
  * Files Found: 1, Files Processed: 1, Files Skipped: 0, Files Failed: 0
  * Signals Created: 0 (The signal insert is rejected, logged as `DUPLICATE_SIGNAL` warning, and execution continues).
