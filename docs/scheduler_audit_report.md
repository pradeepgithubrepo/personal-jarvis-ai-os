# Jarvis Scheduler Reliability Audit Report

## 1. Existing Capabilities Found

During Phase 1, we audited the Jarvis codebase to check for logging, heartbeat, and database structures that track scheduled executions. The findings were:
- **`pipeline_runs` Table**: Tracks pipeline runs including `run_id`, `run_type` (`SCHEDULED`, `ADHOC`, `BACKFILL`), `started_at`, `completed_at`, `status`, and `duration_seconds`.
- **`runtime_events` Table**: Logs system-wide `startup` and `shutdown` events.
- **`JarvisScheduler`**: Runs a background `APScheduler` instance that periodically triggers the `runtime_heartbeat` task (every 30 seconds), but this heartbeat was only logged to standard out / file loggers via loguru and was not persisted to the database.

---

## 2. Gaps Identified

While `pipeline_runs` tracks high-level execution details of the intelligence pipeline itself, Jarvis had several gaps in proving scheduled execution occurred when unattended:
- No persistent history of periodic scheduler heartbeats in the database to verify the scheduler was active during unattended times.
- No record of host/machine environment context (`machine_name`) where scheduled runs occurred, making sleep/wake or hardware-specific troubleshooting difficult.
- No explicit capability to answer whether the machine woke and executed specifically while unattended.

---

## 3. New Implementation

We implemented a lightweight, robust heartbeat monitoring mechanism:
1. **Database Table**: Created the `scheduler_heartbeat` table to track tasks, start/end timestamps, duration, status, and machine hostnames.
2. **SQLAlchemy Model**: Added [SchedulerHeartbeat](file:///home/prad/petprojects/ai/jarvis/storage/models/scheduler_heartbeat.py) to manage the schema and auto-generate the table.
3. **Repository Layer**: Added [SchedulerHeartbeatRepository](file:///home/prad/petprojects/ai/jarvis/storage/repositories/scheduler_heartbeat_repository.py) to handle database inserts, updates, and exceptions cleanly.
4. **Execution Hooks**: 
   - Wrapped `JarvisScheduler.runtime_heartbeat` with the heartbeat hook to log periodic scheduler health.
   - Wrapped `PipelineOrchestrator.run_pipeline` with the heartbeat hook to capture ingestion, qualification, and stage completions or failures.

---

## 4. Validation Results

We verified the database records successfully:
- Heartbeats are recorded as `STARTED` upon task kickoff.
- On success, heartbeats are updated to `COMPLETED` along with their duration.
- On exception, heartbeats capture the specific exception details in the status (e.g. `FAILED: <error_message>`).

### Required Query Verification

```sql
SELECT
task_name,
execution_start,
execution_end,
duration_seconds,
status
FROM scheduler_heartbeat
ORDER BY execution_start DESC;
```

**Output Example:**
```text
pipeline_run_scheduled|2026-06-29 03:06:52.292603|2026-06-29 03:06:52.311468|0|FAILED: Simulated Ingestion Failure
```

---

## Final Recommendation

```text
HEARTBEAT MONITORING IMPLEMENTED
```
