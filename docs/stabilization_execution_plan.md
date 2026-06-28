# Stabilization Execution Plan

This plan details the action items to stabilize Module 4 (Financial Agent & Aggregation) without redesigning any component.

---

## Action Items

### 1. Aggregation Schema Migration
- **Validation Issue**: `sqlite3.OperationalError: no such column: monthly_spending_summary.accounting_spend`
- **Files to Modify**: [database.py](file:///home/prad/petprojects/ai/jarvis/storage/db/database.py)
- **Proposed Changes**: Ensure that the migration script in `initialize_database()` is always run at startup and handles creating the V2 columns (`total_debits`, `total_credits`, `accounting_spend`, `lifestyle_spend`, `total_income`, `net_cash_flow`, `internal_transfers`, `insurance_premiums`, `investments`, `refund_offsets`) if they do not exist.
- **Risks**: Schema lockups if a write occurs during alteration.
- **Validation Approach**: Verify the schema changes by querying the table columns via `sqlite3` command or script.

### 2. Direct Import Failure Fix
- **Validation Issue**: Financial Agent direct import fails unless dependent SQLAlchemy models are preloaded.
- **Files to Modify**: [__init__.py](file:///home/prad/petprojects/ai/jarvis/storage/models/__init__.py)
- **Proposed Changes**: Add explicit imports of all models inside `storage/models/__init__.py` so importing any part of the model package registers all classes with SQLAlchemy's metadata.
- **Risks**: Circular import warnings (handled by keeping imports standard).
- **Validation Approach**: Run a simple python one-liner `python -c "import services.financial_agent"` to ensure it imports without error.

### 3. Null Safety Hardening
- **Validation Issue**: Crashes on `entities.monetary_value = null` or `amount = None`.
- **Files to Modify**: [financial_agent.py](file:///home/prad/petprojects/ai/jarvis/services/financial_agent.py)
- **Proposed Changes**:
  - Update `_extract_amount` to safely check `isinstance(monetary_value, dict)` and return `None` if it isn't, falling back gracefully to text/regex checks.
  - In `_update_merchant_profile`, initialize and default all fields to `0.0` or `0` if they are `None` (e.g. `(profile.lifetime_spend or 0.0)`).
- **Risks**: None.
- **Validation Approach**: Run replay and verify that previously failing signals (e.g. 130, 168, 201) process successfully.

### 4. Transfer Detection & Refund Linkage Improvements
- **Validation Issue**: Undetected transfer pairs and unlinked refunds.
- **Files to Modify**: [financial_agent.py](file:///home/prad/petprojects/ai/jarvis/services/financial_agent.py)
- **Proposed Changes**:
  - Run the batch-finalization method `finalize_batch()` at the end of the pipeline execution to link the credit and debit legs, matching them to `INTERNAL_TRANSFER`.
  - Update the refund matcher to properly set the `refund_of_fact_id` and correct exclusions at the fact level.
- **Risks**: Potential performance slowdown on very large datasets (mitigated by using indexed query filtering).
- **Validation Approach**: Run verification and count the number of finalized transfer pairs (should find at least 8 pairs).

### 5. Salary Candidate Persistence
- **Validation Issue**: Large unmatched credits (>= ₹20,000) are categorised as `INCOME_OTHER` instead of persisting a salary candidate.
- **Files to Modify**: [financial_agent.py](file:///home/prad/petprojects/ai/jarvis/services/financial_agent.py)
- **Proposed Changes**: In `_detect_salary`, Tier 4 checks should write a `SalaryEvent` and save a pending `SalarySource` before returning `INCOME_SALARY_CANDIDATE` as the fact type.
- **Risks**: None.
- **Validation Approach**: Verify the output fact tables for type `INCOME_SALARY_CANDIDATE` on large transaction credits.

### 6. Orchestrator Activation
- **Validation Issue**: Orchestrator calls legacy paths instead of locked Module 4 path.
- **Files to Modify**: [pipeline_orchestrator.py](file:///home/prad/petprojects/ai/jarvis/services/pipeline_orchestrator.py)
- **Proposed Changes**: Verify and ensure the orchestrator calls `FinancialAgent.process_all_understood_financial_signals()` and `AggregationService.run_all()` instead of any legacy `SignalProcessor` or `FinancialIntelligenceService` outflow logic.
- **Risks**: Breakage in automated scheduling pipeline (tested via shadow execution first).
- **Validation Approach**: Run `PipelineOrchestrator.run_pipeline()` and check the logs.
