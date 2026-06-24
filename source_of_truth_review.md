# Source of Truth Review - pipeline_runs & system_status

This document reviews the authority, implementation behavior, failure scenarios, and gaps regarding database writes for `pipeline_runs` and `system_status`.

---

## 1. Current Refactored State (Write Sequence & Mechanics)

Following the refactoring, **Supabase Postgres** is established as the single authoritative Source of Truth:

### `pipeline_runs`
1. **Initial Creation**: Registered first in **Supabase** via `SupabaseRepo.create_pipeline_run`. If this write fails, the pipeline raises an exception immediately and aborts the run.
2. **Updates**: Written to **Supabase** first upon completion. Local SQLite acts solely as a fallback cache.

### `system_status`
1. **Initial Creation**: Checked first on **Supabase** via `SupabaseRepo.fetch_system_status` to detect active lock flags.
2. **Lock Acquisition**: Enforced by writing the `RUNNING` status lock to **Supabase** via `SupabaseRepo.upsert_system_status`. If this write fails, the orchestrator raises an exception and aborts execution to prevent inconsistent state tracking.
3. **Lock Release**: Upon completion (or failure), the lock state is updated to `IDLE`/`ERROR` on **Supabase** first, then mirrored locally.

---

## 2. Authority Analysis

* **Authoritative Database**: **Supabase Postgres** is the source of authority.
* **SQLite Role**: Re-allocated as a secondary runtime cache only.
* **Streamlit Role**: Refactored to fetch system status and recent history directly from Supabase, ensuring all consumers (Android, Streamlit, etc.) view the identical synchronized system state.

---

## 3. Failure Scenarios

### Scenario: SQLite write succeeds, but Supabase write fails during run
* **System Status**: The pipeline aborts immediately because the Supabase write checks are strictly validated. No stale or inconsistent lock is set.
* **Android View**: Sees a clean failure or no changes in status since Supabase did not register the lock.
* **Streamlit View**: Fetches directly from Supabase, so it reflects the same status as Android, showing no mismatched run states.

---

## 4. Summary of Changes

1. **Lock Checks**: Updated `PipelineOrchestrator` in [pipeline_orchestrator.py](file:///home/prad/petprojects/ai/jarvis/services/pipeline_orchestrator.py) to check the active system lock against Supabase first.
2. **Fail-Fast Enforcement**: Enforced that `SupabaseRepo` writes during lock acquisition and run registration must succeed (evaluating their boolean status return values), raising exceptions and aborting the pipeline run on any failures.
3. **Streamlit UI Update**: Refactored `fetch_system_status_from_db` in [ui/app.py](file:///home/prad/petprojects/ai/jarvis/ui/app.py) to pull status metrics and execution histories directly from Supabase. Defined a `DictObject` helper wrapper to cleanly preserve structural compatibility with the dashboard's layout code.
