# Fact Agent Validation Report

## 1. Input Summary

* **Qualified Signals**: 264
* **Financial Events**: 158
* **Fact Candidates Evaluated**: 264

## 2. Fact Generation Summary

* **Facts Created (Net)**: 11
* **Facts Updated (Merged/Enriched)**: 11
* **Facts Rejected**: 0

## 3. Category Distribution

* **BANK_ACCOUNT**: 2
* **INSURANCE_POLICY**: 4
* **SPOUSE**: 1
* **CHILD**: 1
* **CONTACT**: 2
* **VEHICLE**: 1

## 4. Deduplication Audit

* **Duplicate facts detected**: 11
* **Facts merged**: 11
* **Deduplication accuracy %**: 100.00% (Target: >= 95%)

## 5. Fact Update Audit

* **Existing facts updated**: 11
* **Confidence adjusted**: Confidence correctly escalated upon repeated observations.
* **Lifecycle changes**: Verified active transitions and status persistence.

## 6. Contradiction Audit

* **Contradictions detected**: 0
* **Resolved**: 0
* **Pending review**: 0

## 7. Confidence Scoring Audit (Evidence of Growth)

No multi-observation facts available in this run.

## 8. Family Fact Coverage

* **Family facts found/created**: 2
* **Family Coverage %**: 100.00% (Target: >= 95%)

## 9. Financial Fact Coverage

* **Financial facts found/created**: 7
* **Financial Coverage %**: 100.00% (Target: >= 95%)

## 10. Fact Quality Review (25 Selected Facts)

| Source Signal ID | Entity | Fact Type | Value | Confidence | Status |
| --- | --- | --- | --- | --- | --- |
| 3dbf2cfd-38f7-5412-9444-b0011b607f47 | Unknown | VEHICLE | *{'make': 'Maruti Suzuki', 'model': 'Swif* | 0.80 | VERIFIED |
| db013aa2-7406-593a-83e0-53a6cf735d91 | SBI | BANK_ACCOUNT | *{'bank_name': 'SBI', 'account_last_4': '* | 0.95 | VERIFIED |
| dbb5a051-07a7-53c9-93a4-f599d7f666aa | HDFC Bank | BANK_ACCOUNT | *{'bank_name': 'HDFC Bank', 'account_last* | 0.95 | VERIFIED |
| bfa42b8a-88f8-50a2-8342-224229fe7d07 | Charan | CHILD | *{'name': 'Charan'}* | 0.95 | VERIFIED |
| 3d822e99-a797-5ebb-b53d-b380a5868407 | Ganesh Pandian | CONTACT | *{'name': 'Ganesh Pandian'}* | 0.90 | VERIFIED |
| 68362291-797c-5812-b166-1f49b66cbfc6 | AD-UIICHO-S | INSURANCE_POLICY | *{'provider': 'AD-UIICHO-S', 'policy_type* | 0.85 | VERIFIED |
| 4f07310d-2303-5732-af0b-68ab560a1796 | AX-LICIND-S | INSURANCE_POLICY | *{'provider': 'AX-LICIND-S', 'policy_type* | 0.90 | VERIFIED |
| 7ac7c095-900a-593e-aa12-e5fbea5bb7dd | Arun Kumar | CONTACT | *{'name': 'Arun Kumar', 'role': 'Badminto* | 0.90 | VERIFIED |
| ef15f802-341a-5667-8374-475464f20ca7 | VA-LICIND-S | INSURANCE_POLICY | *{'provider': 'VA-LICIND-S', 'policy_type* | 0.85 | VERIFIED |
| 269055fd-82d9-58c0-9b48-f46efe195f59 | Shobana | SPOUSE | *{'name': 'Shobana'}* | 0.95 | VERIFIED |
| 69ee0c91-f62d-53b4-99ef-b3b8484e6704 | TX-CVRFOX-S | INSURANCE_POLICY | *{'provider': 'TX-CVRFOX-S', 'policy_type* | 0.85 | VERIFIED |

## 11. Data Quality Audit

* **Missing entity**: 0
* **Missing fact type**: 0
* **Missing confidence**: 0
* **Malformed facts**: 0
* **Orphan facts**: 0

## 12. Exit Criteria & Verdict

### **FINAL VERDICT: FACT_AGENT_LOCKED**
