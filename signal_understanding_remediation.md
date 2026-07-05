# Signal Understanding Agent: Remediation Audit Report

## 1. Missing Amount Root Cause Analysis (RCA)

We audited the 33 financial contracts flagged with missing monetary amounts. The root causes fall into three distinct categories:

* **Category A: Model/Rule Failed to Identify Amount** (Hit count: 24)
  - *Rule Engine False Positives*: Matched future TDR/STDR mature/credit credits (e.g., 'will be credited') using the rule engine, but the raw messages contain no actual transaction amounts.
  - *LLM Parsing Failure*: The model completely omitted the `monetary_value` object or returned an empty `entities: {}` block in its output.

* **Category B: Model Identified Amount but Placement Failed** (Hit count: 9)
  - The local `qwen2.5:1.5b` model correctly identified the amount and currency but incorrectly structured it under the `bills` or other custom fields in the JSON response instead of the `monetary_value` field.

## 2. Full Trace For All 33 Contracts

| Signal ID | Path | Raw Amt | LLM Response | Structured Ext. | Canonical | Persisted | Category | Root Cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 597 | LLM | NO | NO | NO | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |
| 587 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 581 | LLM | YES | NO | NO | NO | NO | A | Model failed to identify and extract the amount from the raw message. |
| 568 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 546 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 540 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 477 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 450 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 446 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 382 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'bills' instead of 'monetary_value'. |
| 374 | LLM | YES | NO | NO | NO | NO | A | Model failed to identify and extract the amount from the raw message. |
| 370 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 356 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'monetary_value' instead of 'monetary_value'. |
| 344 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'monetary_value' instead of 'monetary_value'. |
| 332 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 331 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 319 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 309 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 303 | RULE_ENGINE | NO | NO | YES | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |
| 298 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'bills' instead of 'monetary_value'. |
| 294 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'bills' instead of 'monetary_value'. |
| 289 | RULE_ENGINE | NO | NO | YES | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |
| 287 | LLM | NO | NO | NO | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |
| 284 | RULE_ENGINE | NO | NO | YES | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |
| 265 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 258 | LLM | YES | NO | NO | NO | NO | A | Model failed to identify and extract the amount from the raw message. |
| 251 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 232 | LLM | YES | YES | NO | NO | NO | A | Model failed to output entities block in response (returned empty entities dict). |
| 228 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'bills' instead of 'monetary_value'. |
| 176 | LLM | YES | YES | YES | NO | NO | B | Model extracted amount correctly but placed it in the wrong entity field: 'bills' instead of 'monetary_value'. |
| 142 | LLM | YES | NO | NO | NO | NO | A | Model failed to identify and extract the amount from the raw message. |
| 651 | LLM | NO | NO | NO | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |
| 11 | LLM | NO | NO | YES | NO | NO | A | Raw message is future-tense TDR/STDR or limit update notification and contains no actual transaction amount. Emitting FINANCIAL class was a rule engine false positive. |

## 3. Financial Entity Coverage Audit

* **Total Financial Contracts**: 164
* **Amount Present**: 131
* **Amount Missing**: 33
* **Amount Coverage %**: 79.88% (Target: 100%, Min: 99%)

> [!WARNING]
> **REMEDIATION REQUIRED**: Financial coverage is below the mandatory 99% threshold.

## 4. Merchant Coverage Audit

* **Merchant Present**: 99
* **Merchant Missing**: 65
* **Merchant Coverage %**: 60.37% (Target: 95%+)

> [!WARNING]
> **REMEDIATION REQUIRED**: Merchant coverage is below the mandatory 95% threshold.

## 5. Taxonomy Violations

1. **Rule Engine Matches Future Transactions**: The `financial_transaction` rule in `SignalUnderstandingAgent` matches `'credited'` unconditionally. This matches future-tense notifications (TDR/STDR mature credits), violating the financial boundary rules.
2. **LLM Schema Deviations**: Local `qwen2.5:1.5b` model occasionally structures amounts under `entities.bills` rather than `entities.monetary_value` when the signal looks like a utility or credit card payment.

## 6. Critical Failure RCA

* **Omission of entities.monetary_value key**: In 24 LLM runs, the model returned empty entities, causing the extraction parser to yield null amounts.
* **Deterministic Route Mismatch (Fixed)**: The medical appointment rule previously failed to emit the `FyiAgent` route despite having an `INFORMATION` class, which was patched and corrected.

## 7. Recommended Fixes

1. **Enhance Rule Engine Financial Boundaries**: Update the `financial_transaction` rule to ignore matches containing future-tense indicators like `'will be credited'`, `'will be debited'`, or `'matured on'` to prevent false positives.
2. **Implement Defensive Entity Extraction Normalization**: Add a normalization layer in `process_signal` to check if `monetary_value` is missing or null, and if so, search for amount fields under other structures (like `bills.amount` or `bills.bill_amount`) and migrate them to `monetary_value` automatically.
3. **Regex Fallback for Amount Extraction**: If a signal is classified as `FINANCIAL` but `monetary_value.amount` is null, perform a regex amount sweep on the raw message to pull and populate the amount programmatically.

## 8. Final Verdict

### **FINAL VERDICT: SUA_REMEDIATION_REQUIRED**
