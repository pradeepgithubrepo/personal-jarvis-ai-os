# Ingestion Inflow Remediation Plan

**Date:** 2026-06-28  
**Component:** Ingestion Remediation Plan  

---

## 1. Remediation Strategy

To implement complete file tracking, batch control, and record lineage without rewriting the upstream loaders or agents, we will layer the following database and logic changes:

### Database Enhancements

1. **Modify `processed_files` Table:**
   Add metric columns:
   * `total_records` INT (Count of signals found in the file)
   * `saved_records` INT (Count of signals successfully saved to the database)
   * `skipped_records` INT (Count of signals skipped due to duplicates or formatting errors)

2. **Add Lineage Column to `mobile_signals`:**
   Add `processed_file_id` (FOREIGN KEY referencing `processed_files.id`) to the `mobile_signals` table.

---

## 2. Implementation Logic Layering

* **Consumer Service Update (`consumer/consumer_service.py`):**
  When a file is parsed:
  1. Calculate metrics (`total`, `saved`, `skipped`) during processing.
  2. Write the file record with these metrics.
  3. When saving signals to the database, include the newly created `processed_file_id` foreign key.

* **Reconciliation Validation:**
  Ensure the record sync script includes the new columns.

---

## 3. Implementation Effort Estimate

* **Database DDL update (Supabase + SQLite):** ~10 mins
* **Consumer Service updates:** ~20 mins
* **Validation and Sync tests:** ~10 mins
* **Total Estimate:** ~40 mins
