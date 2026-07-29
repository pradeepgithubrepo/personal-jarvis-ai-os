# ROUTING_RULES.md — Signal Routing Rules

> Jarvis V2 · Phase 2B  
> Produced: 2026-07-10

---

## Overview

Routing rules are **purely deterministic**. No LLM is involved in routing decisions. Rules are defined in `src/intelligence/routing/routing_rules.py`.

---

## Primary Routing Table

| Signal Type | Primary Agents | Notes |
|-------------|---------------|-------|
| `FINANCIAL` | `financial_agent` | Always dispatched |
| `ACTION`    | `todo_agent` | Always dispatched |
| `FYI`       | `fyi_agent` | Always dispatched |
| `FACT`      | `fact_agent` | Always dispatched |
| `NOISE`     | _(none)_ | Pipeline terminates. No dispatch. |

---

## Conditional Routes

Applied **after** primary routing when contract flags trigger additional agents.

### Rule C-1: FINANCIAL + `memory_candidate=True`

```
Signal:   FINANCIAL
Contract: memory_candidate = True
Result:   financial_agent, fact_agent
```

**Rationale:** A financial signal that is also a memory candidate (e.g., "School fee paid to XYZ School") should be recorded as a financial event AND persisted as a long-term fact (e.g., the relationship between the user and the school).

**Example:**
```
"School fee paid to Sample School — INR 45,000"
→ financial_agent  (process the debit)
→ fact_agent       (store school enrollment fact)
```

---

### Rule C-2: ACTION + `memory_candidate=True`

```
Signal:   ACTION
Contract: memory_candidate = True
Result:   todo_agent, fact_agent
```

**Rationale:** An action that also reveals persistent facts about the user's world (e.g., "Call Dr. Sharma for Chinicka's appointment") should create a todo AND store the doctor's name as a fact.

---

## Rules NOT in Scope for Phase 2B

The following routing enhancements are deferred to later phases:

| Rule | Phase |
|------|-------|
| FYI + calendar integration | Phase 4 |
| NOISE with high-confidence recovery queue | Phase 5 |
| Cross-signal deduplication before routing | Phase 5 |

---

## Route Decision Examples

| Input | `memory_candidate` | Route |
|-------|--------------------|-------|
| FINANCIAL | False | `[financial_agent]` |
| FINANCIAL | True | `[financial_agent, fact_agent]` |
| ACTION | False | `[todo_agent]` |
| ACTION | True | `[todo_agent, fact_agent]` |
| FYI | True (always) | `[fyi_agent]` |
| FACT | True (always) | `[fact_agent]` |
| NOISE | False (always) | `[]` |

---

## Implementation

```python
# src/intelligence/routing/routing_rules.py

PRIMARY_ROUTING_TABLE = {
    "FINANCIAL": ["financial_agent"],
    "ACTION":    ["todo_agent"],
    "FYI":       ["fyi_agent"],
    "FACT":      ["fact_agent"],
    "NOISE":     [],
}

CONDITIONAL_ROUTES = [
    {
        "condition_signal_types": ["FINANCIAL"],
        "condition_flag": "memory_candidate",
        "condition_value": True,
        "additional_agents": ["fact_agent"],
    },
    {
        "condition_signal_types": ["ACTION"],
        "condition_flag": "memory_candidate",
        "condition_value": True,
        "additional_agents": ["fact_agent"],
    },
]
```

---

*Document: ROUTING_RULES.md*  
*Phase 2B — Routing Layer + Canonical Contract Governance*
