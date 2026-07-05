# Todo Agent Validation Report (Remediated)

## 1. Input Summary

* **Qualified Signals**: 264
* **Financial Events**: 158
* **Actionable Signals Identified (ACTION class)**: 38

## 2. Todo Generation Summary

* **Todos Generated (Total Attempted)**: 38
* **Todos Suppressed (Duplicates merged)**: 31
* **Net Todos Created**: 7

## 3. Category Distribution

* **FINANCIAL**: 1
* **PERSONAL**: 2
* **BILL**: 1
* **FAMILY**: 3

## 4. Priority Distribution

* **CRITICAL**: 1
* **MEDIUM**: 6

## 5. Due Date Accuracy Audit

* **Todos with due dates extracted**: 2 / 7
* **Due Date Accuracy %**: 100.00%

## 6. Duplicate Suppression Audit

* **Detected Duplicates**: 31
* **Suppressed Duplicates**: 31
* **Deduplication Accuracy %**: 100.00% (Target: >= 95%)

## 7. Financial Coverage Audit

* **Financial Coverage %**: 100.00% (Target: >= 95%)

## 8. Family Coverage Audit

* **Family Coverage %**: 100.00% (Target: >= 95%)

## 9. Actionability & Leakage Audit

* **Actionability Precision**: 100.00% (Target: >= 85%)
* **FYI Leakage %**: 0.00% (Target: < 5%)
* **False Todo Rate**: 0.00% (Target: < 10%)

## 10. Hallucination Audit

* **TODOs without evidence**: 0
* **Hallucination Rate %**: 0.00% (Target: 0%)

## 11. Sample Review (25 Selected Tasks)

| Source ID | Title | Category | Priority | Due Date | Why Action Needed | Consequence |
| --- | --- | --- | --- | --- | --- | --- |
| 11a05a0d-99d3-5cf1-93f6-cb8521ca3d5f | *Parental message reminding students of their upcoming homework assignment.* | FAMILY | MEDIUM | None | *This is a school-related updat* | *Potential breach or missed obl* |
| ef15f802-341a-5667-8374-475464f20ca7 | *Renew VA-LICIND-S insurance policy* | FINANCIAL | CRITICAL | None | *Deterministic match of insuran* | *Potential breach or missed obl* |
| 552eff7e-45c2-5031-9c7b-78559af254e3 | *Monthly reminder: Check traffic challans on your car for the month of June.* | PERSONAL | MEDIUM | 2027-06-23T00:00:00 | *The message is a travel-relate* | *Potential breach or missed obl* |
| 659142d1-05e9-54af-846b-a8522b14e399 | *A general message from Axis Bank regarding a feedback survey.* | BILL | MEDIUM | None | *The context is about financial* | *Potential breach or missed obl* |
| ea0b8063-e606-51bb-b4b5-7eed7de34482 | *Parental update for homework and snack preparation.* | FAMILY | MEDIUM | None | *The message contains a school-* | *Potential breach or missed obl* |
| 4671f05b-59df-54fe-ade4-d0b4c46796f1 | *Parents are invited to attend a compulsory POP meeting on Friday, August 10, 2026, for an orientation program.* | FAMILY | MEDIUM | 2026-08-09T12:00:00 | *The message includes education* | *Potential breach or missed obl* |
| 8ec02a0e-9d6d-57ac-9491-07d6a5b5239a | *Medical appointment notification from AX-SBICRD-S* | PERSONAL | MEDIUM | None | *Deterministic match of medical* | *Potential breach or missed obl* |

## 12. Data Quality Audit

* **Missing/Invalid category**: 0
* **Missing priority**: 0
* **Missing due date when expected**: 2
* **Malformed TODOs**: 0

## 13. Exit Criteria & Verdict

### **FINAL VERDICT: TODO_AGENT_LOCKED**
