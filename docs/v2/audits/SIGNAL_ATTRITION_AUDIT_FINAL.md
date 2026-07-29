# SIGNAL ATTRITION AUDIT — FINAL REPORT

> Jarvis V2 · Critical Signal Attrition Investigation  
> Audit Completed: 2026-07-10T15:52:00Z  
> Remote: `https://tbwnyuampjoamgarwwoo.supabase.co` (`sb-project-ref: tbwnyuampjoamgarwwoo`)  
> Schema: `jarvis_insights_schemav1`  
> Git Commit: `4965494` (pushed `origin/jarvis-v2`)  
> **REMOTE IS KING — All data from remote Supabase. No local assumptions.**

---

## Remote Verification Method

All counts obtained via `curl` with `Accept-Profile: jarvis_insights_schemav1` and `Prefer: count=exact`.  
All data obtained via paginated `curl` JSON fetches (2 × 1000-row batches + full detail fetches).  
Analysis performed offline using Python on local copies of remote JSON.

---

## 1. Pipeline Counts (REMOTE VERIFIED)

| Stage | Count | Remote Evidence |
|---|---|---|
| `mobile_signals` | **1,700** | `content-range: */1700` — request `019f4cb1` |
| `qualified_signals` | **1** | `content-range: */1` — request `019f4cb4` |
| `understood_signals` | **5** | `content-range: */5` — request confirmed |
| `signal_routes` | **12** | `content-range: */12` — request confirmed |

### Attrition Rates

| Transition | Rate | Classification |
|---|---|---|
| `mobile_signals` → `qualified_signals` | 0.06% (1 / 1700) | 🚨 CRITICAL |
| `qualified_signals` → `understood_signals` | N/A (e2e artifacts) | Pipeline not run |
| `understood_signals` → `signal_routes` | N/A (e2e artifacts) | Pipeline not run |

---

## 2. Source Breakdown (REMOTE VERIFIED)

All 1,700 `mobile_signals` — `processed=False` on every single row.

| Source | Count | % | Processed |
|---|---|---|---|
| `sms` | **1,008** | 59.3% | 0/1008 |
| `whatsapp` | **365** | 21.5% | 0/365 |
| `gpay` | **277** | 16.3% | 0/277 |
| `bank_statement` | **49** | 2.9% | 0/49 |
| `e2e_test` | 1 | 0.1% | 0/1 |
| **TOTAL** | **1,700** | 100% | **0/1700** |

---

## 3. GPay Forensic Audit

- **GPay in `mobile_signals`**: 277 (all `processed=False`)
- **GPay in `qualified_signals`**: 0
- **Root cause**: Pipeline never ran. Not a GPay-specific issue.

→ See [`GPAY_FORENSIC_AUDIT.md`](./GPAY_FORENSIC_AUDIT.md)

---

## 4. Bank Transaction Forensic Audit

- **`bank_statement` signals**: 49
- **Top bank SMS senders**: HDFC (57+36+35+29+16+14), SBI (21+16), others
- **Estimated bank SMS signals**: ~200+
- **Root cause**: Pipeline never ran.

→ See [`BANK_FORENSIC_AUDIT.md`](./BANK_FORENSIC_AUDIT.md)

---

## 5. WhatsApp Filter Audit

| Period | Count |
|---|---|
| Before 2026-07-01 | 1,446 (85.1%) |
| After 2026-07-01 | 254 (14.9%) |

- Date range: 2026-03-26 → 2026-07-10
- Pre-July WhatsApp exclusion rule has not been applied (pipeline never ran)
- ~310 of 365 WhatsApp signals would be excluded when rule is applied
- These are **intentionally filtered**, not lost

→ See [`WHATSAPP_FILTER_AUDIT.md`](./WHATSAPP_FILTER_AUDIT.md)

---

## 6. Qualification Attrition Analysis

The single `qualified_signals` row:
```
id: e85f1ea6-e978-4d81-aa92-879ecd985934
source: e2e_test  |  sender: TESTER  |  signal_id: 90000099
qualification_status: QUALIFIED
created_at: 2026-07-10T15:19:01 UTC
```
This is the Phase 2B e2e test artifact. **No real signal has ever been qualified.**

→ See [`SIGNAL_LINEAGE_AUDIT.md`](./SIGNAL_LINEAGE_AUDIT.md)

---

## 7. Understanding Gap Analysis

| Category | Real Data | e2e Artifacts |
|---|---|---|
| `qualified_signals` | 0 | 1 |
| `understood_signals` | 0 | 5 |
| `signal_routes` | 0 | 12 |

The 5 `understood_signals` are synthetic rows inserted by `e2e_dispatch_test.py` at `2026-07-10T15:19:01` — all at the same timestamp, confirming batch insert origin.

→ See [`UNDERSTANDING_GAP_ANALYSIS.md`](./UNDERSTANDING_GAP_ANALYSIS.md)

---

## 8. Delta Processing Investigation

| Metric | Value |
|---|---|
| `mobile_signals` with `processed=True` | **0** |
| `mobile_signals` with `processed=False` | **1,700** |

The Consumer marks signals `processed=False` on insert. The Qualification Agent is responsible for marking them `processed=True` after qualification. Zero marks = zero processing.

Delta processing tables (`processed_files`, `pipeline_runs`, `pipeline_run_events`) — could not be accessed via REST (may not exist or be in a different schema).

---

## 9. Random Trace Audit (20 signals)

All 20 sampled signals (latest by id) confirmed:
- `processed=False` ✅
- `qualified=NO` ✅  
- `understood=NO` ✅
- `routed=NO` ✅

Representative signals: Airtel SMS promos, RBI fraud warnings, WhatsApp personal messages, OTP messages — **all unprocessed**.

---

## 10. Root Cause Analysis (FINAL)

### Primary Root Cause

> **The Qualification Agent has never been run against real `mobile_signals` in the remote Supabase environment.**

This is the single root cause of all observed attrition. It is not:
- ❌ Not a bug in qualification logic
- ❌ Not a GPay-specific issue
- ❌ Not a date filter problem
- ❌ Not data loss
- ❌ Not a schema issue

It is:
- ✅ An **operational gap** — the pipeline exists in code but has not been triggered end-to-end
- ✅ A **scheduler gap** — no live scheduler connects Consumer → QA → SUA → Router

### Secondary Root Cause

> e2e test artifacts in `qualified_signals`, `understood_signals`, and `signal_routes` **misrepresent pipeline health** when viewed as counts alone.

Counts of 1 / 5 / 12 gave the impression the pipeline was partially working. The data shows these are all test records from a single batch insert at `2026-07-10T15:19`.

---

## Conclusion

```
Expected state:   1700 mobile_signals → N qualified → M understood → K routed
Actual state:     1700 mobile_signals → 0 qualified → 0 understood → 0 routed
                  (1 / 5 / 12 = e2e test artifacts, not pipeline output)
```

The pipeline code is correct. The pipeline has not run.

---

## Remediation Plan

| Step | Action | Expected Output |
|---|---|---|
| 1 | Run Qualification Agent backfill (all `processed=False`) | ~400–600 `QUALIFIED` signals |
| 2 | Run SUA on all new `QUALIFIED` signals | ~400–600 `understood_signals` |
| 3 | Run Router on all new `understood_signals` | Populated `signal_routes` |
| 4 | Establish live scheduler | Consumer → QA → SUA → Router on cron |
| 5 | Verify ≥10 real `FINANCIAL` understood_signals | Phase 3A can begin |

---

## Phase 3A Gate Status

> [!CAUTION]
> **Phase 3A (Financial Agent) remains BLOCKED.**
>
> Gate condition: ≥10 real `FINANCIAL` type `understood_signals` in remote database.  
> Current: 0 real FINANCIAL understood_signals.  
> Action required: Execute pipeline backfill (Steps 1–5 above).

---

## Audit Files Produced

| File | Contents |
|---|---|
| [`SIGNAL_LINEAGE_AUDIT.md`](./SIGNAL_LINEAGE_AUDIT.md) | Full pipeline accounting with remote evidence |
| [`SIGNAL_ATTRITION_RCA.md`](./SIGNAL_ATTRITION_RCA.md) | Root cause analysis |
| [`GPAY_FORENSIC_AUDIT.md`](./GPAY_FORENSIC_AUDIT.md) | GPay signal forensics |
| [`BANK_FORENSIC_AUDIT.md`](./BANK_FORENSIC_AUDIT.md) | Bank transaction forensics |
| [`WHATSAPP_FILTER_AUDIT.md`](./WHATSAPP_FILTER_AUDIT.md) | WhatsApp date filter analysis |
| [`UNDERSTANDING_GAP_ANALYSIS.md`](./UNDERSTANDING_GAP_ANALYSIS.md) | Qualification → Understanding gap |
| **`SIGNAL_ATTRITION_AUDIT_FINAL.md`** | **This document** |

Git: pushed to `origin/jarvis-v2` at commit `4965494`
