# ROUTING_ARCHITECTURE.md — Phase 2B Routing Layer

> Jarvis V2 · Phase 2B  
> Produced: 2026-07-10

---

## Overview

Phase 2B introduces the **Routing Layer** — the infrastructure that bridges the Signal Understanding Agent (SUA) output to downstream specialist agents.

```
Consumer (mobile_signals)
    ↓
Qualification Agent (qualified_signals)
    ↓
Signal Understanding Agent → contract_json in understood_signals
    ↓
┌─────────────────────────────────────────────────┐
│           ROUTING LAYER (Phase 2B)              │
│                                                 │
│   ContractValidator → SignalRouter              │
│                    ↓                            │
│           RouteDecision                         │
│                    ↓                            │
│         ContractDispatcher                      │
│                    ↓                            │
│        signal_routes (audit table)              │
└─────────────────────────────────────────────────┘
    ↓             ↓            ↓           ↓
financial_   todo_agent   fyi_agent   fact_agent
  agent       (stub)       (stub)      (stub)
  (stub)
    ↓
Daily Brief (Phase 4)
```

---

## Governing Principle

> **LLMs Interpret. Agents Own Business Logic.**

The SUA uses an LLM to interpret raw text and produce a typed `contract_json`. The routing layer and all downstream agents operate on this contract only. No downstream component ever receives or inspects raw signal text.

> **Build Constitution BC-5:** The canonical contract is the only interface between SUA and downstream agents.

---

## Components

### 1. ContractValidator (`src/intelligence/contracts/contract_validator.py`)

**Role:** Gate-keeper. Validates every contract before routing.

**Validates:**
- All required fields are present
- `signal_type` is a valid enum value (FINANCIAL | ACTION | FYI | FACT | NOISE)
- `importance` and `confidence` are in `[0.0, 1.0]`
- Candidate flags are consistent with `signal_type`
- `contract_version` equals `1`

**On failure:** Rejects contract, logs errors, writes `VALIDATION_FAILED` to `signal_routes`. Never dispatches.

---

### 2. SignalRouter (`src/intelligence/routing/router.py`)

**Role:** Validate contract and resolve target agents.

**Inputs:** `understood_signal` dict (from `understood_signals` table)  
**Output:** `RouteDecision` with `route_to: list[str]`

**Steps:**
1. Enrich contract from top-level `understood_signals` fields
2. Delegate to `ContractValidator`
3. On success: call `resolve_route()` from `routing_rules.py`
4. Return `RouteDecision`

---

### 3. Routing Rules (`src/intelligence/routing/routing_rules.py`)

**Role:** Define which agents receive which signals. Pure deterministic data.

See `ROUTING_RULES.md` for the full rule table.

---

### 4. ContractDispatcher (`src/intelligence/dispatch/dispatcher.py`)

**Role:** Execute the route decision. Invoke each target agent. Record audit trail.

**For each agent in `route_to`:**
1. Resolve agent from `dispatch_registry`
2. Write `DISPATCHED` row to `signal_routes`
3. Call `agent.process(contract)`
4. Write `COMPLETED` or `FAILED` row to `signal_routes`

**Multi-route:** All agents in `route_to` are invoked. Failure of one does not prevent others (isolated per-agent try/except).

---

### 5. Dispatch Registry (`src/intelligence/dispatch/dispatch_registry.py`)

**Role:** Map agent name strings to agent instances.

**Phase 2B:** All entries point to stubs.  
**Phase 3+:** Real agents replace stubs via `register_agent()`.

---

### 6. Agent Stubs (`src/agents/stubs/`)

**Role:** Interface placeholders for Phase 3+ agents.

| Agent | Stub File | Phase |
|-------|-----------|-------|
| `financial_agent` | `financial_agent_stub.py` | Phase 3A |
| `todo_agent`      | `todo_agent_stub.py`      | Phase 3B |
| `fyi_agent`       | `fyi_agent_stub.py`       | Phase 3C |
| `fact_agent`      | `fact_agent_stub.py`      | Phase 3D |

---

### 7. signal_routes Table

**Role:** Full routing audit trail. Every dispatch creates a row per agent.

**Owner:** `ContractDispatcher` (only writer — Build Constitution AD-3)

**Statuses:** `DISPATCHED` | `COMPLETED` | `FAILED` | `SKIPPED` | `VALIDATION_FAILED` | `NO_ROUTE`

---

### 8. ReplayRouter (`src/intelligence/replay/replay_router.py`)

**Role:** Re-dispatch a specific `understood_signal` without re-running SUA/Qualification/Consumer.

**Use cases:**
- Recovery from dispatch failures
- Re-routing after routing rule changes
- Testing new agent implementations against historical contracts

**Preserves audit trail:** Previous `signal_routes` rows are not deleted — new rows are appended.

---

## Data Flow Diagram

```
understood_signals.contract_json
            │
            ▼
   ContractValidator
     ┌──────┴───────┐
   VALID          INVALID
     │               │
     ▼               ▼
 SignalRouter   VALIDATION_FAILED
     │          → signal_routes
     ▼
 RouteDecision
  route_to: [...]
     │
     ▼
ContractDispatcher
     ├─── financial_agent → signal_routes (DISPATCHED → COMPLETED/FAILED)
     ├─── fact_agent      → signal_routes (DISPATCHED → COMPLETED/FAILED)
     └─── (future agents)
```

---

*Document: ROUTING_ARCHITECTURE.md*  
*Phase 2B — Routing Layer + Canonical Contract Governance*
