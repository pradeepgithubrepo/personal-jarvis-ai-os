# DISPATCH_FRAMEWORK.md — Agent Dispatch Framework

> Jarvis V2 · Phase 2B  
> Produced: 2026-07-10

---

## Overview

The Dispatch Framework is the execution layer of Phase 2B. It takes a `RouteDecision` from the `SignalRouter` and invokes each target agent, recording a full audit trail in `signal_routes`.

---

## Components

### ContractDispatcher

**File:** `src/intelligence/dispatch/dispatcher.py`

**Input:** `RouteDecision`  
**Output:** `DispatchResult`

**Behaviour:**
1. If `route_decision.is_valid == False` → write `VALIDATION_FAILED` audit row. Return.
2. If `route_decision.has_routes == False` (NOISE) → write `NO_ROUTE`. Return.
3. For each `agent_name` in `route_decision.route_to`:
   - Look up agent in registry
   - Write `DISPATCHED` audit row
   - Call `agent.process(contract)`
   - Write `COMPLETED` or `FAILED` audit row
4. Return aggregate `DispatchResult`

**Isolation:** Each agent is wrapped in its own try/except. One agent failing does not prevent others from executing.

---

### Dispatch Registry

**File:** `src/intelligence/dispatch/dispatch_registry.py`

Maps agent name strings → agent instances.

```python
_REGISTRY = {
    "financial_agent": FinancialAgentStub(),
    "todo_agent":      TodoAgentStub(),
    "fyi_agent":       FyiAgentStub(),
    "fact_agent":      FactAgentStub(),
}
```

**Adding a new agent (Phase 3+):**
```python
from src.intelligence.dispatch.dispatch_registry import register_agent
from src.agents.financial.agent import FinancialAgent  # real Phase 3A agent

register_agent("financial_agent", FinancialAgent())
```

---

### DispatchResult

```python
@dataclass
class DispatchResult:
    understood_signal_id: str
    signal_type: str
    total_routes: int
    completed: int
    failed: int
    skipped: int
    records: list[AgentDispatchRecord]
    validation_errors: list[str]

    @property
    def overall_status(self) -> str:
        # "VALIDATION_FAILED" | "NO_ROUTE" | "SUCCESS" | "PARTIAL_SUCCESS" | "FAILED"
```

---

### signal_routes Audit Rows

For every dispatch, rows are written to `signal_routes`:

| Scenario | Rows Written |
|----------|-------------|
| Invalid contract | 1 row: `agent=__validation__`, `status=VALIDATION_FAILED` |
| NOISE signal | 0 rows (pipeline terminates silently) |
| FINANCIAL → financial_agent | 2 rows: DISPATCHED → COMPLETED (or FAILED) |
| FINANCIAL + memory_candidate → 2 agents | 4 rows: 2×DISPATCHED, 2×COMPLETED |

---

## Multi-Route Example

Signal: `"School fee paid to XYZ School — INR 45,000"`  
SUA classification: `FINANCIAL`, `memory_candidate=True`

```
RouteDecision.route_to = ["financial_agent", "fact_agent"]

Dispatcher:
  1. financial_agent.process(contract)
     → signal_routes: (DISPATCHED → COMPLETED)
  2. fact_agent.process(contract)
     → signal_routes: (DISPATCHED → COMPLETED)

DispatchResult:
  total_routes=2, completed=2, overall_status="SUCCESS"
```

---

## Agent Interface Contract

All agents (stub or real) implement:

```python
class BaseAgentStub(ABC):
    @property
    @abstractmethod
    def agent_name(self) -> str: ...

    @abstractmethod
    def process(self, contract: dict) -> AgentResult: ...
```

**Critical:** `process()` receives **only** the `contract` dict — never raw signal text. Downstream agents are permanently isolated from raw data by this interface.

---

## Future Extension

To add a new downstream agent:

1. Create agent class implementing `BaseAgentStub`
2. Replace stub registration in `dispatch_registry.py`
3. Delete the stub (Build Constitution BC-2)
4. No changes needed to `ContractDispatcher` or routing rules

---

*Document: DISPATCH_FRAMEWORK.md*  
*Phase 2B — Routing Layer + Canonical Contract Governance*
