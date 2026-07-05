# Ingestion Gap Analysis

**Date:** 2026-06-28  
**Component:** Ingestion Gap Analysis  

---

## 1. Capability Gap Matrix

| Capability | Current State | Gap |
| :--- | :--- | :--- |
| **File Tracking** | **PARTIAL** | Filename and hash are tracked in `processed_files`, but we lack tracking for record counts, skipped items, and errors. |
| **Batch Tracking** | **NONE** | No `ingestion_batches` table or equivalent batch identifier exists to group loads together. |
| **Duplicate Detection**| **EXISTS** | Safe hash checks exist on a file level (`ProcessedFile.file_hash`) and message level (`MobileSignal.message_hash`). |
| **Lineage** | **NONE** | No foreign key linkage exists between `mobile_signals`/`signals` and the `processed_files` registry to identify origin files. |

---

## 2. Gaps and Gaps Impact

* **No Record-to-File Lineage:** Without a `file_id` or `batch_id` foreign key on the signals table, it is impossible to identify which mobile signals were loaded by a specific file ingestion event. This prevents auditing or rolling back a bad file load.
* **Missing Batch Metrics:** `processed_files` only captures status (`PROCESSED`, `FAILED`, `SKIPPED`) without logging counts of how many records were loaded, skipped, or failed.
