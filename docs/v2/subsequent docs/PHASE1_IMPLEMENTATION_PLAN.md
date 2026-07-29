# Financial Agent Phase 1: Implementation Plan

## Readiness Summary

### What Already Exists
- PDF extraction engine (`pypdf`) in [pdf_parser.py](file:///home/prad/petprojects/ai/jarvis/src/agents/consumer/parsers/pdf_parser.py) — reusable as-is
- GPay PDF parser with regex extractors in [gpay_collector.py](file:///home/prad/petprojects/ai/jarvis/src/agents/consumer/collectors/gpay_collector.py) — 278 transactions extracted accurately
- SBI/HDFC PDF parsers in [bank_statement_collector.py](file:///home/prad/petprojects/ai/jarvis/src/agents/consumer/collectors/bank_statement_collector.py) — partially broken (see defects below)
- Financial agent stub in [financial_agent_stub.py](file:///home/prad/petprojects/ai/jarvis/src/agents/stubs/financial_agent_stub.py) — stub only, no real logic
- `understood_signals` table with 132 FINANCIAL-classified records — live in Supabase
- Pipeline event logging infrastructure — reusable

### What Must Be Built
1. `financial_transactions` ledger table in Supabase
2. `merchant_normalization_rules` override table in Supabase
3. Financial Agent (`src/agents/financial/`) replacing the stub, with stages:
   - Transaction extraction (SMS, GPay, Statement)
   - Spam/qualification filter
   - Duplicate detection engine
   - Internal transfer detector
   - Merchant normalizer (Stage 1 deterministic + Stage 2 LLM)
4. Runner script `scripts/run_financial_agent.py`
5. Unit tests `tests/test_financial_agent.py`

### Defects to Fix First
1. **SBI multi-page parser bug** ([bank_statement_collector.py L12-14](file:///home/prad/petprojects/ai/jarvis/src/agents/consumer/collectors/bank_statement_collector.py#L12-L14)): Missing `break` in `start_idx` scan causes early pages to be skipped
2. **HDFC parser DEBIT/CREDIT detection**: Relies only on text keywords (`CR`, `CREDIT`) — misclassifies many debits as credits
3. **Financial SMS spam leakage**: 75% of FINANCIAL-classified signals are promotions/offers (no `transaction_type` guard)

---

## Implementation Sequence

| Step | What | Guard |
| :--- | :--- | :--- |
| **0** | Fix SBI parser bug + HDFC DEBIT/CREDIT detection | Remote validate: 49→correct count |
| **1** | Create `financial_transactions` + `merchant_normalization_rules` tables via SQL migration | Remote validate: tables visible |
| **2** | Build `FinancialAgent` core + SMS spam filter + canonical extraction | Unit tests pass |
| **3** | Build duplicate detection engine (deterministic, no LLM) | Remote validate against known matches |
| **4** | Build internal transfer detector (HDFC↔SBI rules) | Remote validate: 2 known transfers flagged |
| **5** | Build merchant normalization Stage 1 (deterministic rules dict) | Unit tests pass |
| **6** | Build merchant normalization Stage 2 (LLM + user retrofit cache) | LLM bypass tested |
| **7** | Build `run_financial_agent.py` runner + backfill | Remote validate: ledger row counts |
| **8** | Write unit tests for all stages | All tests green |

---

## LLM Usage Rules (Hard Constraint)
- ✅ LLM allowed: Merchant normalization Stage 2, category recommendation
- ❌ LLM forbidden: Spam filter, duplicate detection, transfer detection, amount/date extraction
