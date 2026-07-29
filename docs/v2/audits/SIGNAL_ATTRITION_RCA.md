# SIGNAL ATTRITION ROOT CAUSE ANALYSIS

> Jarvis V2 · SIGNAL_ATTRITION_RCA  
> Executed: 2026-07-10T15:47:00Z  
> Remote: `https://tbwnyuampjoamgarwwoo.supabase.co`  
> Schema: `jarvis_insights_schemav1`  
> **REMOTE IS KING**

---

## Executive Summary

The observed signal attrition is **not a bug in the pipeline logic**.  
It is **a pipeline that has never run**.

```
1,700 mobile_signals    →   0 qualified   →   0 understood   →   0 routed
```

All data in `qualified_signals` (1 row), `understood_signals` (5 rows), and `signal_routes` (12 rows) are artifacts from the Phase 2B E2E validation test and have **no relationship to real signal data**.

---

## Question 1: Why do 1,700 mobile_signals become 1 qualified_signal?

**Answer: The Qualification Agent has never been run against real data.**

Remote evidence:
- `mobile_signals` count: **1,700** (all `processed=False`)
- `qualified_signals` count: **1** (source=`e2e_test`, sender=`TESTER`, created `2026-07-10T15:19:01`)
- The single `qualified_signals` row was inserted by `scratch/e2e_dispatch_test.py`, not by the Qualification Agent

**Root cause**: The Consumer pipeline ingested 1,700 signals into `mobile_signals` but the Qualification Agent scheduler/trigger has never fired, never been deployed, or was not running.

Supporting evidence: `processed=False` on ALL 1,700 rows. The qualification step marks signals `processed=True` after reading them. Zero marks = zero processing attempts.

---

## Question 2: Why do 1 qualified_signal become 5 understood_signals?

**Answer: The understood_signals are also e2e test artifacts.**

The `e2e_dispatch_test.py` script manually inserted 5 synthetic signals directly into `understood_signals`, bypassing the SUA entirely. These are not the output of any real understanding run.

---

## Question 3: Is this expected?

**Partially expected, partially not.**

What is expected:
- Phase 2A (SUA) and Phase 2B (Routing) were built but not connected to a live scheduler
- The SUA was validated using a local shadow validation run, not a live pipeline run
- Signal accumulation (1,700 signals) is normal for a system in development

What is NOT expected:
- 1,700 signals should have been processed as part of SUA shadow validation
- The `processed` flag should reflect at least some pipeline activity
- No pipeline run evidence exists in the remote database

---

## Question 4: Is this healthy?

**No.** A pipeline with 1,700 backlogged unprocessed signals and zero real qualification output is not healthy. However, it is recoverable: the data is intact, the pipeline code exists, and a single scheduled run would process all 1,700.

---

## Question 5: Is this a bug?

**Partially.** The pipeline code itself is correct (proven by unit tests and e2e test). The bug is **operational**: the Qualification Agent scheduler is not running against the remote database.

---

## Question 6: Is this a backlog?

**Yes.** 1,700 signals are backed up waiting for the first real pipeline run. These span from **2026-03-26 to 2026-07-10** (over 3.5 months).

---

## Question 7: Is this configuration drift?

**Likely.** The local environment runs against the remote Supabase, but the scheduled pipeline processes have not been triggered. The system was built incrementally (Consumer → Qualification → SUA → Routing) but never stitched together end-to-end in a live scheduled loop.

---

## Question 8: Is this data loss?

**No.** All 1,700 signals are safely stored in `mobile_signals` with `processed=False`. They are available for processing at any time. No data has been lost.

---

## Root Cause Summary

| Root Cause | Evidence | Severity |
|---|---|---|
| Qualification Agent never ran | `processed=False` on all 1,700 rows | CRITICAL |
| No live pipeline scheduler | No `pipeline_runs` evidence | CRITICAL |
| SUA never ran on real data | `understood_signals` = 0 real rows | CRITICAL |
| 1,700 signal backlog | Date range: Mar–Jul 2026 | HIGH |
| e2e artifacts misrepresent pipeline state | `qualified_signals` = 1 (test only) | MEDIUM |

---

## Recommended Fixes

1. **Run Qualification Agent backfill** — process all 1,700 `mobile_signals` where `processed=False`
2. **Run SUA** — feed all `QUALIFIED` signals through the SUA to populate `understood_signals`
3. **Run Routing Layer** — dispatch all `understood_signals` through SignalRouter and ContractDispatcher
4. **Establish live scheduler** — ensure Consumer → QA → SUA → Router runs on a schedule
5. **Add pipeline run tracking** — write records to `pipeline_runs` table for every execution

---

## Can Phase 3A (Financial Agent) Begin?

> [!CAUTION]
> **NO** — not until the real pipeline has run and produced real `understood_signals` of type `FINANCIAL`.
>
> Current state: 0 real FINANCIAL signals have been understood.
> The Financial Agent has no real data to consume.
>
> Phase 3A can begin only after:
> 1. Backfill run produces real `qualified_signals`
> 2. SUA run produces real `understood_signals` (including `FINANCIAL` type)
> 3. At least 10 real FINANCIAL signals are confirmed in `understood_signals`
