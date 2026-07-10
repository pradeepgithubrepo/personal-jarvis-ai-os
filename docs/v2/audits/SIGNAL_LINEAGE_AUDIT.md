# SIGNAL LINEAGE AUDIT

> Jarvis V2 · Critical Audit  
> Executed: 2026-07-10T15:47:00Z  
> Remote: `https://tbwnyuampjoamgarwwoo.supabase.co`  
> Schema: `jarvis_insights_schemav1`  
> **REMOTE IS KING — All data from remote Supabase only.**

---

## Remote Verification Evidence

| Verification Method | Result |
|---|---|
| curl HTTP HEAD count for `mobile_signals` | `content-range: */1700` |
| curl HTTP HEAD count for `qualified_signals` | `content-range: */1` |
| curl HTTP HEAD count for `understood_signals` | `content-range: */5` |
| curl HTTP HEAD count for `signal_routes` | `content-range: */12` |
| curl JSON fetch `mobile_signals` (1700 rows in 2 batches) | ✅ Complete |
| curl JSON fetch `understood_signals` | ✅ Complete |
| curl JSON fetch `qualified_signals` (all rows) | ✅ Complete |

Remote Request IDs:
- `mobile_signals count`: `019f4cb1-f294-72ac-a5bd-cbbf726e2702`
- `qualified_signals count`: `019f4cb4-6318-76de-9711-5aa02a29aec8`

---

## OBJECTIVE 1 — Full Pipeline Accounting (REMOTE VERIFIED)

| Stage | Count | Rate | Attrition |
|---|---|---|---|
| `mobile_signals` | **1,700** | 100% (baseline) | — |
| `qualified_signals` | **1** | 0.06% | **99.94%** 🚨 |
| `understood_signals` | **5** | — | — (e2e artifact only) |
| `signal_routes` | **12** | — | — (e2e artifact only) |

> [!CAUTION]
> **The 1 qualified_signal and 5 understood_signals are ALL artifacts from the e2e Phase 2B test run.** They are not real pipeline output. The real pipeline has processed **0 signals end-to-end.**

**True pipeline state:**
```
1700 mobile_signals  →  0 qualified  →  0 understood  →  0 routed
```

---

## OBJECTIVE 2 — Source Breakdown (REMOTE VERIFIED)

All 1,700 `mobile_signals` fetched and analyzed. **`processed=False` for all 1,700 signals.**

| Source | Count | % of Total | Processed |
|---|---|---|---|
| `sms` | **1,008** | 59.3% | 0 |
| `whatsapp` | **365** | 21.5% | 0 |
| `gpay` | **277** | 16.3% | 0 |
| `bank_statement` | **49** | 2.9% | 0 |
| `e2e_test` | 1 | 0.1% | 0 |

**Total `processed=True`: 0 / 1700**

### Top Senders
| Sender | Count |
|---|---|
| pprad | 308 |
| AT-AIRTEL-P | 61 |
| AD-HDFCBK-S | 57 |
| AT-AIRTEL-S | 43 |
| JM-HDFCBK-S | 36 |
| VM-HDFCBK-T | 35 |
| VM-HDFCBK-S | 29 |
| VK-SBICRD-T | 21 |

---

## OBJECTIVE 5 — WhatsApp Date Filter (REMOTE VERIFIED)

| Period | Count |
|---|---|
| Before 2026-07-01 | **1,446** (85.1%) |
| After 2026-07-01 | **254** (14.9%) |
| No timestamp | 0 |

**Date range**: 2026-03-26 → 2026-07-10

The pre-July WhatsApp exclusion rule would eliminate a significant portion of signals if applied. However, the filter is **moot** since nothing has been processed at all.

---

## OBJECTIVE 7 — Understanding Gap (REMOTE VERIFIED)

- `qualified_signals` with real data: **0** (the 1 row is an e2e artifact)
- `understood_signals` with real data: **0** (all 5 are e2e artifacts)
- **Gap**: The qualification pipeline has never been run against real data

The 5 `understood_signals` were manually inserted by the Phase 2B validation script and reference the e2e test `qualified_signal_id`.

---

## OBJECTIVE 8 — Delta Processing State (REMOTE VERIFIED)

| Flag | mobile_signals |
|---|---|
| `processed=True` | **0** |
| `processed=False` | **1,700** |

The Consumer (`consumer.py`) ingests signals from Supabase Storage and inserts them into `mobile_signals`. **It sets `processed=False` on insert.** The Qualification Agent is supposed to pick them up and mark them `processed=True` after processing. Since none are marked `processed=True`, the Qualification Agent has **never run** or **failed silently on every attempt.**

> [!WARNING]
> Additional delta tables (`processed_files`, `pipeline_runs`, `pipeline_run_events`) could not be read — the tables may not exist or have different names. This requires direct verification.

---

## OBJECTIVE 9 — 20 Signal Trace Sample (REMOTE VERIFIED)

| # | id | source | processed | qualified | understood |
|---|---|---|---|---|---|
| 1 | 90000099 | e2e_test | False | YES (e2e) | YES (e2e) |
| 2 | 10038 | whatsapp | False | NO | NO |
| 3 | 10037 | whatsapp | False | NO | NO |
| 4 | 10036 | sms | False | NO | NO |
| 5 | 10035 | sms | False | NO | NO |
| 6 | 10034 | sms | False | NO | NO |
| 7 | 10033 | sms | False | NO | NO |
| 8 | 10032 | sms | False | NO | NO |
| 9 | 10031 | sms | False | NO | NO |
| 10 | 10030 | sms | False | NO | NO |
| 11 | 10029 | sms | False | NO | NO |
| 12 | 10028 | sms | False | NO | NO |
| 13 | 10027 | sms | False | NO | NO |
| 14 | 10026 | sms | False | NO | NO |
| 15 | 10025 | sms | False | NO | NO |
| 16 | 10024 | sms | False | NO | NO |
| 17 | 10023 | sms | False | NO | NO |
| 18 | 10022 | sms | False | NO | NO |
| 19 | 10021 | sms | False | NO | NO |
| 20 | 10019 | sms | False | NO | NO |

**Every real signal: qualified=NO, understood=NO, routed=NO.**

Sample content of recent signals:
- `id=10038`: "Verify delta processing works!" (WhatsApp)
- `id=10036`: "Your Airtel pack on 9445XXX128 is about to expire!" (SMS)
- `id=10035`: Tamil-language RBI fraud warning (SMS)
- `id=10034`: "Ab aap Airtel Insider hai" Airtel promo (SMS)
