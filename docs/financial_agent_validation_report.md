# Financial Agent Validation Report

Date: 2026-06-25  
Module: Module 4 - Financial Agent  
Dataset: Existing local production SQLite cache at `storage/db/sqlite/jarvis.db`  
Validation mode: Replay of existing production `understood_signals` into isolated copy `/tmp/jarvis_module4_validation.db`

---

## Executive Summary

Module 4 is not ready to lock.

The active production cache contains 203 raw/qualified signals and 100 understood contracts, including 81 contracts with `FINANCIAL` in `classes`. However, the production `financial_events` and `financial_facts` tables are empty. To avoid mutating production state, validation replayed the 81 financial contracts through the current `FinancialAgent.process_contract()` implementation on a copied SQLite database.

Replay produced 78 financial facts and 3 processing failures. Aggregation failed because the local `monthly_spending_summary` table is still on the legacy schema (`total_spend`) and does not contain the V2 columns required by `AggregationService` (`accounting_spend`, `lifestyle_spend`, `total_income`, `net_cash_flow`, etc.).

Major blockers:

- Financial Agent direct import fails unless dependent SQLAlchemy models are preloaded.
- 3 of 81 financial contracts fail during processing.
- Internal transfer detection found only 1 transfer pair while at least 9 amount/time candidate pairs remain undetected.
- Salary detection produced 0 salary events.
- Refund processing produced 1 refund fact, but it was unlinked and not excluded from accounting/lifestyle spend at fact level.
- Merchant resolution resolved 0 facts to seeded merchant rows.
- 54 of 78 facts have confidence below 0.85.
- Aggregation cannot run against the current SQLite schema.
- The orchestrator still calls legacy `SignalProcessor` and `FinancialIntelligenceService` paths instead of the locked Module 4 path.

Final decision: **REQUIRES REWORK**

---

## Validation Statistics

Source database state before replay:

| Table | Count |
|---|---:|
| `mobile_signals` | 203 |
| `qualified_signals` | 203 |
| `understood_signals` | 100 |
| `financial_events` | 0 |
| `financial_facts` | 0 |
| `transfer_pairs` | 0 |
| `salary_events` | 0 |
| `salary_sources` | 0 |
| `merchants` | 30 |

Qualification breakdown:

| Status | Count |
|---|---:|
| `QUALIFIED` | 100 |
| `REVIEW` | 56 |
| `REJECTED` | 47 |

Understanding breakdown:

| Signal Type | Path | Count |
|---|---|---:|
| `financial_transaction` | `RULE_ENGINE` | 63 |
| `financial_transaction` | `LLM` | 21 |
| `general` | `RULE_ENGINE` | 9 |
| `travel_booking` | `RULE_ENGINE` | 3 |
| `general` | `LLM` | 2 |
| `delivery_update` | `RULE_ENGINE` | 1 |
| `school_update` | `LLM` | 1 |

Replay results:

| Metric | Count |
|---|---:|
| Financial contracts replayed | 81 |
| Facts created | 78 |
| Processing failures | 3 |
| Transfer pairs created | 1 |
| Salary events created | 0 |
| Refund facts created | 1 |
| Aggregation run | Failed |

Processing failures:

| Signal ID | Summary | Failure |
|---|---|---|
| 130 | `Transaction of INR 909.0 at AX-UIICHO-S` | `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'float'` |
| 168 | `Received INR 2,000.00 in HDFC Bank account.` | `AttributeError: 'NoneType' object has no attribute 'get'` because `entities.monetary_value` is `null` |
| 201 | `Transaction of INR 450.0 at zomato` | `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'float'` |

---

## Transfer Detection

Detected transfers: 1 pair.

| Debit Event | Credit Event | Amount | Window | Keyword | Confidence | Assessment |
|---:|---:|---:|---:|---|---:|---|
| 71 | 70 | 150000.00 | 12 seconds | `YONO` | 1.0 | Likely true positive |

Detected transfer details:

| Field | Value |
|---|---|
| Debit title | `Transaction of INR 150000.0 at pradee ac x3221 dt 02` |
| Debit sender/account text | `JK-SBYONO-S`, `pradee ac x3221 dt 02` |
| Credit title | `Received INR 1,50,000.00 in HDFC Bank Account for PRADEEP via IMPS on 02-05-26...` |
| Receiver account text | HDFC account from credit summary |
| Transfer type | `YONO` |
| Window seconds | 172800 |
| Confidence | 1.0 |

Candidate false negatives found by amount/time scan:

| Debit | Credit | Amount | Time Gap | Notes |
|---:|---:|---:|---:|---|
| 1 | 2 | 2000.00 | 0.002h | SBI debit to HDFC credit, likely transfer |
| 15 | 16 | 58000.00 | 0.001h | HDFC/SBI pair candidate |
| 17 | 16 | 58000.00 | 0.001h | SBI sender alias pair candidate |
| 22 | 21 | 15000.00 | 0.009h | HDFC credit pair candidate |
| 37 | 36 | 52000.00 | 0.000h | IMPS/HDFC pair candidate |
| 56 | 55 | 2500.00 | 0.003h | HDFC credit pair candidate |
| 63 | 64 | 20000.00 | 0.001h | own-account text candidate |
| 65 | 64 | 20000.00 | 0.007h | SBI sender alias pair candidate |
| 72 | 70 | 150000.00 | 0.013h | alternate debit leg for detected credit |

Transfer validation metrics:

| Metric | Count |
|---|---:|
| Detected transfers | 1 |
| True positives | 1 likely |
| False positives | 0 observed in detected set |
| False negatives | At least 8 likely, 9 candidate pairs total |

Assessment: transfer detection is not lock-ready. The algorithm appears order-sensitive because it only detects while processing debit contracts and only sees credit events already written. Many debit/credit pairs with matching amount and near-identical timestamps were not marked as internal transfers.

---

## Salary Detection

Salary events created: 0.

| Tier | Detected | Correct | Incorrect | Missed | Unknown |
|---|---:|---:|---:|---:|---:|
| Tier 1 keyword | 0 | 0 | 0 | Unknown | Unknown |
| Tier 2 registry | 0 | 0 | 0 | Not applicable; registry empty | 0 |
| Tier 3 recurring | 0 | 0 | 0 | Unknown | Unknown |
| Tier 4 large credit | 0 salary facts | 0 | 0 | At least 4 review candidates logged as `INCOME_OTHER` | 4 |

Large unmatched credits observed:

| Signal | Amount | Result | Detection Reason |
|---:|---:|---|---|
| 54 | 58000.00 | `INCOME_OTHER` | Logged as large unclassified credit |
| 83 | 52000.00 | `INCOME_OTHER` | Logged as large unclassified credit |
| 165 | 20000.00 | `INCOME_OTHER` | Logged as large unclassified credit |
| 189 | 150000.00 | `INCOME_OTHER` | Logged as large unclassified credit |

Assessment: salary detection is not validated successfully. The code logs Tier 4 large unclassified credits but does not persist a salary candidate fact type or salary event. The empty `salary_sources` registry also means Tier 2 cannot operate.

---

## Refund Validation

Refund facts created: 1.

| Refund | Merchant | Amount | Original Transaction | Offset Month | Accounting Spend Reduced |
|---|---|---:|---|---|---|
| Signal 22 | None / `JD-HDFCBK-S` sender | 7791.00 | Not linked | None | Reduced only by manual aggregation logic, not fact-level linkage |

Observed refund fact state:

| Field | Value |
|---|---|
| `fact_type` | `REFUND_EVENT` |
| `refund_of_fact_id` | `NULL` |
| `is_excluded_from_accounting_spend` | `False` |
| `is_excluded_from_lifestyle_spend` | `False` |
| `refund_applied_to_month` | `NULL` |

Assessment: refund processing is not lock-ready. The refund is recognized as a refund event, but it is not linked to the matching expense and is not excluded at fact level. The aggregation implementation subtracts refund facts during rollup, but aggregation could not run due schema mismatch.

---

## Merchant Resolution

Merchant resolution results:

| Resolution Type | Count |
|---|---:|
| Known merchant via `merchant_id` | 0 |
| Alias resolved | 0 |
| Raw fallback | 61 |
| No merchant / income-like fact | 17 |

Top fallback/unknown merchant strings:

| Merchant String | Count | Amount |
|---|---:|---:|
| `AX-SBIPSG-T` | 8 | 245500.00 |
| `AD-SBIPSG-T` | 6 | 453500.00 |
| `AD-CBSSBI-S` | 4 | 137094.00 |
| `AD-HDFCBK-S` | 4 | 74913.00 |
| `7308080808` | 3 | 132204.00 |
| `VM-HDFCBK-S` | 3 | 11500.00 |
| `VM-SBICRD-S` | 3 | 1180.00 |
| `JD-HDFCBK-S` | 2 | 60000.00 |
| `AX-CBSSBI-S` | 2 | 30853.00 |
| `5676791` | 2 | 3359.00 |

Assessment: merchant resolution is not effective on the current dataset. Most merchant strings are bank sender IDs, account fragments, or phone/reference numbers rather than true merchants. This appears partly upstream: SUA merchant extraction often emits sender aliases or account text as merchant.

---

## Spending Validation

`AggregationService.run_all()` failed:

```text
sqlite3.OperationalError: no such column: monthly_spending_summary.accounting_spend
```

The active SQLite schema for `monthly_spending_summary` still contains legacy columns:

| Column | Present |
|---|---|
| `summary_id` | yes |
| `month_key` | yes |
| `total_spend` | yes |
| `transaction_count` | yes |
| `accounting_spend` | no |
| `lifestyle_spend` | no |
| `total_income` | no |
| `net_cash_flow` | no |

Manual rollup from replayed facts:

| Month | Accounting Spend | Lifestyle Spend | Income | Net Cash Flow | Internal Transfers | Refund Offsets | Insurance | Investments |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-04 | 285300.00 | 275500.00 | 0.00 | -285300.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| 2026-05 | 445007.00 | 432562.00 | 172500.00 | -272507.00 | 150000.00 | 0.00 | 1127.00 | 0.00 |
| 2026-06 | 620664.00 | 614382.00 | 127402.82 | -493261.18 | 0.00 | 7791.00 | 3141.00 | 0.00 |

Manual sample of 20 facts found repeated issues:

| Issue Type | Observed |
|---|---:|
| `EXPENSE_UNCLASSIFIED` in sample | 12 |
| Zero amount despite amount in title/contract | 3 |
| Likely missed internal transfer pairs | 3 |
| Correct-looking credit-card bill classifications | 2 |
| Correct-looking insurance/lifestyle exclusions | Not enough in sample |

Assessment: spending totals cannot be trusted for lock because aggregation cannot run on the current schema, missed internal transfers inflate spend, zero-amount facts undercount spend, and unlinked refunds are not applied through complete fact lineage.

---

## Category Accuracy

Category distribution:

| Category | Count | Amount | Estimated Precision | Notes |
|---|---:|---:|---:|---|
| `EXPENSE_UNCLASSIFIED` | 53 | 1330235.00 | Low / not useful | Dominates spending facts |
| `BILL_PAYMENT_CC` | 5 | 24259.00 | Medium-high on sampled rows | Several SBI card payments recognized |
| `INSURANCE_PAYMENT` | 3 | 4268.00 | Medium | UIIC/insurance-like rows recognized, but one failed contract also insurance |
| `SHOPPING` | 1 | 0.00 | Low | Amazon Pay row lost amount |

Top merchants by category are mostly unresolved bank aliases, not true merchants. Category accuracy cannot be considered validated while 53 of 62 spending-like facts are `EXPENSE_UNCLASSIFIED`.

Misclassification examples:

| Signal/Title | Observed | Issue |
|---|---|---|
| `HDFC Bank A/C *3221 sent Rs.930.00 from Amazon Pay.` | `SHOPPING`, amount `0.0` | Category plausible, amount lost |
| `Received INR 2,000.00 in HDFC Bank account.` | Processing failure | LLM contract has `monetary_value: null` |
| Multiple SBI/HDFC transfer pairs | `EXPENSE_UNCLASSIFIED` + `INCOME_OTHER` | Likely internal transfers not neutralized |

---

## Confidence Analysis

Confidence histogram:

| Bucket | Count |
|---|---:|
| 0.95+ | 24 |
| 0.90-0.95 | 0 |
| 0.85-0.90 | 0 |
| Below 0.85 | 54 |

Low-confidence facts:

All 53 `EXPENSE_UNCLASSIFIED` facts have `classification_confidence = 0.5`. The Amazon Pay shopping fact has `classification_confidence = 0.8`. These 54 facts are below the auto-process threshold of 0.85.

Assessment: confidence distribution is not acceptable for lock. Most financial facts require review or improved deterministic/category handling.

---

## Boundary Validation

Boundary checks:

| Boundary | Result | Evidence |
|---|---|---|
| Financial Agent does not call LLM semantic parser | Pass | `services/financial_agent.py` does not import `IntelligenceRouter` or call `router.ask` |
| Financial Agent does not modify qualification | Pass | No writes to `qualified_signals` observed in `FinancialAgent` |
| Financial Agent rejects non-financial contracts | Pass | `process_contract()` returns `None` when `FINANCIAL` is absent |
| Financial Agent performs signal understanding | Partial concern | It does not parse raw mobile messages, but `_classify_expense()` uses summary text and `raw_context.sender`; this is acceptable for financial classification, not semantic understanding |
| Aggregation ownership | Mixed | `FinancialAgent` itself writes facts only, but wrapper `process_financial_contract()` triggers `AggregationService.run_for_month()` |
| Runtime orchestrator uses locked path | Fail | `pipeline_orchestrator.py` still calls `SignalProcessor` and `FinancialIntelligenceService`, not `FinancialAgent.process_contract()` over SUA routes |
| Legacy Supabase aggregator boundary | Fail / deferred | `financial_aggregator.py` fetches raw signal messages from Supabase for enrichment, which violates the canonical "downstream agents consume contracts" rule if used as production path |

Assessment: `FinancialAgent` core class mostly respects boundaries, but the active orchestration path does not yet enforce the locked Module 4 architecture.

---

## Known Issues

1. Production financial fact ledger is empty, so Module 4 is not currently materialized on the active dataset.
2. Direct Financial Agent validation fails unless all SQLAlchemy FK target models are preloaded.
3. 3 financial contracts fail during replay.
4. `entities.monetary_value = null` from LLM contracts crashes processing.
5. Merchant profile update appears to fail for some known merchant matches when profile date fields are `None`.
6. Internal transfer detection misses many likely pairs.
7. Internal transfer detection only writes a fact for the debit leg that triggered detection; the already-created credit fact remains `INCOME_OTHER`.
8. Salary detection produces no salary events or salary candidate facts.
9. Refund fact is unlinked and not excluded at fact level.
10. Merchant resolution does not resolve any row to the seeded registry.
11. V2 monthly summary schema is missing in SQLite.
12. Aggregation cannot run.
13. Orchestrator still uses legacy `SignalProcessor` and `FinancialIntelligenceService`.
14. Category accuracy is not measurable at acceptable quality because most rows are `EXPENSE_UNCLASSIFIED`.

---

## Recommendations

Required before lock:

1. Add/execute the SQLite and Supabase migrations for V2 financial rollup columns.
2. Align orchestrator to dispatch SUA contracts to `FinancialAgent`, then run `AggregationService`.
3. Remove or disable legacy `SignalProcessor` and `FinancialIntelligenceService` from the production pipeline path.
4. Harden `FinancialAgent` against `entities.monetary_value = null` and `amount = None`.
5. Fix merchant profile update for first-seen/new profile rows.
6. Make internal transfer detection batch-aware or rerunnable after all financial events are written.
7. Update both legs of detected internal transfers, including existing credit facts.
8. Persist Tier 4 salary candidates distinctly instead of silently leaving them as `INCOME_OTHER`.
9. Implement refund matching and set `refund_of_fact_id`, `refund_applied_to_month`, and spend exclusion flags correctly.
10. Improve SUA merchant extraction or Financial Agent merchant parsing so bank aliases are not treated as merchants.
11. Re-run validation after fixes and produce a new report with real fact tables populated.

Recommended validation additions:

1. Create a repeatable validation script that clones production DB, replays Module 4, and emits metrics.
2. Add assertions for known transfer pairs from this dataset.
3. Add assertions for null monetary values and zero-amount facts.
4. Add a manual review fixture for at least 20 known transactions with expected merchant/category/fact type.

---

## Module Readiness

Decision: **REQUIRES REWORK**

Justification:

Module 4 cannot be locked because the current production dataset does not have materialized financial facts, replay fails on 3 financial contracts, aggregation cannot run on the current schema, transfer detection misses multiple likely internal transfers, refund linkage is incomplete, salary detection produces no persisted salary classifications, and merchant/category resolution is dominated by low-confidence fallbacks.

The architecture remains sound, but the implementation and active pipeline wiring are not yet validated to the standard required by the anchor document. Module 5 should not begin until Module 4 is corrected and this validation is rerun successfully.

