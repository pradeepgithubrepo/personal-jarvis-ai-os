# REPLAY_FRAMEWORK.md — Replay Framework

> Jarvis V2 · Phase 2B  
> Produced: 2026-07-10

---

## Overview

The Replay Framework allows re-dispatching any `understood_signal` by its UUID, without re-running the Consumer, Qualification Agent, or SUA.

This implements Build Constitution **P-6 (Replayable Events)**: every fact in the system traces back to its raw signal, and that chain can be replayed.

---

## What Replay Does

```
Input:  understood_signal_id (UUID)

Replay:
  1. Fetch understood_signals record from Supabase by ID
  2. Re-validate the contract
  3. Re-resolve routing rules
  4. Re-dispatch to target agents
  5. Write new signal_routes audit rows

Output: ReplayResult with dispatch outcome
```

## What Replay Does NOT Do

```
❌ Does NOT re-run Consumer (mobile_signals ingestion)
❌ Does NOT re-run Qualification Agent
❌ Does NOT re-run SUA / LLM inference
❌ Does NOT delete previous signal_routes rows (audit history is preserved)
```

---

## Use Cases

| Scenario | Solution |
|----------|----------|
| Agent dispatch failed (DB down) | Replay after DB recovers |
| Routing rules changed | Replay historical signals to apply new rules |
| New agent added in Phase 3 | Replay selected signals to populate new agent's tables |
| Bug in stub caused wrong status | Replay after fix |
| Auditor needs to trace a specific signal | Replay shows full re-dispatch logs |

---

## Implementation

**File:** `src/intelligence/replay/replay_router.py`

```python
replay = ReplayRouter()
result = replay.replay(
    understood_signal_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
    supabase_client=client,
)

print(result.success)            # True/False
print(result.dispatch_result.overall_status)  # "SUCCESS"
```

---

## Audit Trail

Each replay appends new `signal_routes` rows. Old rows from the original dispatch are never modified or deleted. This preserves full lineage:

```
signal_routes:
  row 1: signal_id=X, agent=financial_agent, status=FAILED       (original dispatch, 2026-07-10 04:00)
  row 2: signal_id=X, agent=financial_agent, status=COMPLETED    (replay, 2026-07-10 05:00)
```

Queries can distinguish original vs replay runs by `created_at` timestamp.

---

## Limitations

- Replay uses the contract **as stored** in `understood_signals.contract_json`. If the SUA has been updated since the original run, the replayed contract may differ from what a fresh SUA run would produce.
- To get a fresh classification, re-run the SUA orchestrator with `run_pipeline()` — not replay.

---

*Document: REPLAY_FRAMEWORK.md*  
*Phase 2B — Routing Layer + Canonical Contract Governance*
