# SIGNAL ROUTING ALIGNMENT REVIEW
**Jarvis V2 Pipeline Rebuild — Stage 3 (Routing Layer)**

---

## 1. Current State Assessment

This section details the current implementation of the Signal Routing layer, covering its database schema, execution logic, and decision engine.

### 1.1 Database Schema (`signal_routes`)
The table was defined in the Phase 2B migration (`sql/migrations/phase2b_signal_routes.sql`):

```sql
CREATE TABLE IF NOT EXISTS jarvis_insights_schemav1.signal_routes (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    understood_signal_id UUID        NOT NULL
                            REFERENCES jarvis_insights_schemav1.understood_signals(id)
                            ON DELETE CASCADE,
    agent_name           TEXT        NOT NULL,
    route_status         TEXT        NOT NULL,   -- DISPATCHED | COMPLETED | FAILED | SKIPPED | VALIDATION_FAILED | NO_ROUTE
    started_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at         TIMESTAMPTZ,
    error_message        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Key Properties of Current Schema:
* **Indexes**: 
  * `idx_signal_routes_understood_signal_id` (on `understood_signal_id`)
  * `idx_signal_routes_agent_name` (on `agent_name`)
  * `idx_signal_routes_route_status` (on `route_status`)
  * `idx_signal_routes_created_at` (on `created_at DESC`)
* **Constraints**: PK on `id`, FK on `understood_signal_id` referencing `understood_signals(id)` with cascade delete.

### 1.2 Routing Logic
Routing decisions are resolved in two steps:
1. **Validation**: The `SignalRouter` (`src/intelligence/routing/router.py`) retrieves the `understood_signals` row, builds the enriched contract, and validates it against `ContractValidator`. If validation fails, the dispatcher writes a `VALIDATION_FAILED` row and terminates.
2. **Deterministic Rules Engine**: The `resolve_route` method (`src/intelligence/routing/routing_rules.py`) resolves targets using pure Python mapping functions:
   * Maps `signal_type` to a list of primary target agents:
     * `FINANCIAL` $\rightarrow$ `["financial_agent"]`
     * `ACTION` $\rightarrow$ `["todo_agent"]`
     * `FYI` $\rightarrow$ `["fyi_agent"]`
     * `FACT` $\rightarrow$ `["fact_agent"]`
     * `NOISE` $\rightarrow$ `[]` (pipeline terminates; no routes)
   * Evaluates conditional rules to append additional targets:
     * If `FINANCIAL` or `ACTION` and `memory_candidate == True` $\rightarrow$ also append `["fact_agent"]`.
* **LLM Usage**: **No LLM is used in the routing layer.** The router is deterministic, utilizing the semantic classification already completed by the Understanding Layer.

---

## 2. Duplication Analysis

We evaluated the current table columns to ensure `signal_routes` functions strictly as a **Dispatch Layer** rather than a **Knowledge Layer**:

| Column Name | Status | Purpose / Reasoning |
|---|---|---|
| `id` | **REQUIRED** | Primary key for row-level audit traceability. |
| `understood_signal_id` | **REQUIRED** | Foreign key linking back to the semantic source of truth. |
| `agent_name` | **REQUIRED** | Identifies the target downstream agent receiving the signal. |
| `route_status` | **REQUIRED** | Tracks execution lifecycle (`DISPATCHED`, `COMPLETED`, `FAILED`). |
| `started_at` | **REQUIRED** | Execution start timestamp (crucial for timeout and latency analysis). |
| `completed_at` | **REQUIRED** | Execution end timestamp. |
| `error_message` | **REQUIRED** | Captures traceback details if a downstream agent fails. |
| `created_at` | **REQUIRED** | Database audit record metadata. |
| `summary` | **REDUNDANT** | Already exists in `understood_signals`. Joining via FK is trivial. |
| `contract_json` | **REDUNDANT** | Already exists in `understood_signals`. Joining via FK is trivial. |
| `metadata` | **REDUNDANT** | Already exists in `understood_signals`. |
| `signal_type` | **REDUNDANT** | Already exists in `understood_signals`. |
| `message` | **REDUNDANT** | Already exists in `mobile_signals` / `qualified_signals`. |

### Risks of Duplicate Columns:
1. **State Divergence**: If an understood signal's contract is replayed or corrected, having duplicate copies of the contract details in the route table would lead to out-of-sync states.
2. **Storage Bloat**: Storing the JSON contract and metadata payload twice for every downstream route adds unnecessary overhead.
3. **Architecture Violation**: Violates Principle 3 (downstream agents must join back to the semantic source of truth for context).

*Verdict*: The current `signal_routes` database table is **already fully clean and free of duplicate semantic data**.

---

## 3. Recommended Schema Alignment

We propose aligning `signal_routes` to include routing metadata and rationale while retaining execution audits.

### Proposed Schema DDL:
```sql
ALTER TABLE jarvis_insights_schemav1.signal_routes 
ADD COLUMN IF NOT EXISTS route_reason TEXT,
ADD COLUMN IF NOT EXISTS route_confidence DOUBLE PRECISION;
```

### Column Justifications:
1. **`route_reason`** (TEXT): Explains *why* the rules engine chose the targets (e.g. *"Primary route [todo_agent] + conditional memory flag [fact_agent]"*). Useful for debugging multi-route decisions.
2. **`route_confidence`** (DOUBLE PRECISION): Copies the confidence from the underlying classification to let downstream systems know the classification strength without needing a JOIN.

---

## 4. Multi-Route Capability

* **Support**: The current design fully supports multi-routing. The rules engine resolves a list of agents, and the `ContractDispatcher` processes them sequentially:
  * For each target agent, a separate row is inserted in `signal_routes`.
  * For example, a utility bill containing both a financial charge and a task due date will result in two rows linked to the same `understood_signal_id`:
    * Row 1: `agent_name = "financial_agent"`, `route_status = "COMPLETED"`
    * Row 2: `agent_name = "todo_agent"`, `route_status = "COMPLETED"`
* **Processing Impact**: High isolation. If the `financial_agent` fails, the `todo_agent` still runs independently, and each failure/success is isolated to its respective audit row.

---

## 5. Lineage Validation

Lineage is completely traceable and enforced at the database level:

```text
    signal_routes (understood_signal_id)
            ↓ [FK cascade delete]
    understood_signals (qualified_signal_id)
            ↓ [FK cascade delete]
    qualified_signals (signal_id)
            ↓ [FK cascade delete]
    mobile_signals (id)
```

No gaps exist. All links are established via unique primary keys and indexed foreign keys.

---

## 6. Alignment with "Accuracy First" Principle

$$\text{False Positive} > \text{False Negative}$$

Under this rule, routing should prefer **delivering an extra route** over **missing a route**.

### Proposed Routing Optimizations:
1. **Action Flag Safety Route**: If the contract flag `requires_action` is `True`, always append `["todo_agent"]` to the route list, even if the primary `signal_type` is `FINANCIAL` or `FYI`.
2. **Ambiguous Default Route**: If `signal_type` is unknown or falls back to `FYI`, dispatch to `["fyi_agent"]` to ensure the information is visible in the downstream feed.

---

## 7. Implementation Adaptation Plan

### Phase 1: Schema Updates (Low-Risk)
* Execute DDL modifications to add `route_reason` and `route_confidence` to `signal_routes`.
* Retain all performance indexes.

### Phase 2: Logic Integration
* Update `resolve_route` in `routing_rules.py` to return both the list of agents and the rule-based reason string.
* Add the Action Flag safety routing condition to the rules list.
* Update `ContractDispatcher` to map the `route_reason` and `route_confidence` columns when writing database rows.

### Phase 3: Migration Strategy
* No data migration is required, as the backfill pipeline has cleared the tables. The updated routing schema will populate naturally on the next backfill run.

### Phase 4: Validation Strategy
* Update the backfill test runner (`run_pipeline_backfill.py`) to re-enable Stage 3 (Routing).
* Verify that:
  1. No signals are lost.
  2. Multi-route signals (e.g. utility bills, financial tasks) successfully generate multiple rows in `signal_routes`.
  3. Validation metrics confirm 0 failures.
