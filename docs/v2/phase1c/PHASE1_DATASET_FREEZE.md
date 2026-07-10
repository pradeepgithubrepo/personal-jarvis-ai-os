# Phase 1 Dataset Freeze Baseline

This document locks the baseline dataset ingested in Phase 1 and frozen for Phase 2 Qualification Agent.

* **Total Signals Frozen:** 1698
* **Backfill Date:** 2026-07-09
* **Schema Version:** `v2.0.0-schemav1`
* **Collector Version:** `v2.0.0-phase1c-backfill`
* **Locked File Count:** 18
* **Known Limitations:**
  - HDFC statement mock data is used for layout validation in unit testing.
  - SMS LITE Top-up represents 1 duplicate transaction which is bypassed dynamically in database writes.
