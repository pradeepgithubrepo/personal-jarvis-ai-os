# Module 1.5 Final Review: System Orchestrator & Scheduler

This review document provides an analysis of the startup sequence, scheduled jobs, failure modes, race conditions, and outlines the target architecture for the **Jarvis Orchestration Pipeline** matching all Module 1.5 requirements.

---

## 1. Startup Sequence (Current State)

```text
app/main.py (Uvicorn Server)
   │
   └── run_runtime() [Daemon Thread]
         │
         └── app/startup.py: startup()
               │
               ├── 1. initialize_system() (Rules, DB schemas, LLM ping) [Blocking]
               ├── 2. ConsumerService().run_sync() [Blocking]
               ├── 3. MobileSignalPipeline().run() [Blocking]
               ├── 4. EmailPipeline().run() [Blocking]
               │
               └── 5. JarvisScheduler().start() [Non-blocking]
```

---

## 2. Job Execution Order, Dependencies, and Frequencies

* **Job Execution Order**: Currently, only `run_consumer_sync()` is registered to execute at periodic intervals. Downstream classification and extraction stages do not run as scheduler jobs.
* **Job Dependencies**: No dependencies are configured.
* **Job Frequencies**: 
  * `runtime_heartbeat`: Runs every 30 seconds.
  * `consumer_sync`: Runs every `settings.consumer_poll_interval_minutes` (configured via env).
* **Recommended Execution Order (Single-Threaded Pipeline)**:
  ```text
  Scheduled Trigger (Refresh Window)
     │
     └── 1. Ingest Raw Signals (ConsumerService.run_sync)
           └── If new files loaded:
                 ├── 2. Structure Raw Signals (MobileSignalPipeline.run)
                 ├── 3. Categorize Signals (SignalProcessor.process_all_signals)
                 ├── 4. Extract Tasks (extract_todos)
                 ├── 5. Extract Financial Events (extract_financial_events)
                 ├── 6. Extract Informational Updates (extract_fyi_events)
                 ├── 7. Outflow Summarization (FinancialIntelligenceService.run_pipeline)
                 └── 8. Daily Rollups (DailyBriefGenerator.generate_brief_for_date)
  ```

---

## 3. Parallelism, Failure Handling, and Shutdown

* **Blocking vs. Parallel**: Jobs run concurrently on BackgroundScheduler thread workers. Because SQLite locks the database on writes and Ollama blocks on CPU/GPU local model queries, running them in parallel can cause database locks and latency spikes. The pipeline should run sequentially.
* **Failure Handling**: Failures currently log stack traces and exit. In the target state, failures will be classified and recorded in the database history registry.
* **Graceful Shutdown**: SIGINT triggers `scheduler.shutdown()` to complete running jobs and release connection pools cleanly.

---

## 4. Potential Race Conditions & Pipeline Locking

* **Overlap Risk**: If a sync run takes longer than the polling interval, a duplicate trigger will run concurrently.
* **Target Lock Design**: Implement a lock flag stored in `system_status.current_status` (e.g., `RUNNING`). If the status is `RUNNING` when a scheduled job triggers, the execution is skipped and a warning is logged.

---

## 5. New Database Requirements (Supabase Schema DDL)

To implement pipeline auditing, status indicators, and completion flags, the following two tables will be introduced into `jarvis_insights_schema`:

### Table 1: `pipeline_runs`
Tracks history and metrics of every execution.

```sql
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.pipeline_runs (
    run_id UUID PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL, -- 'SCHEDULED', 'ADHOC', 'BACKFILL'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL, -- 'RUNNING', 'SUCCESS', 'FAILED'
    files_processed INT DEFAULT 0,
    signals_processed INT DEFAULT 0,
    todos_generated INT DEFAULT 0,
    financial_events_generated INT DEFAULT 0,
    fyi_generated INT DEFAULT 0,
    facts_generated INT DEFAULT 0,
    llm_calls INT DEFAULT 0,
    duration_seconds NUMERIC(10, 2),
    error_message TEXT,
    error_type VARCHAR(50) -- 'INGESTION_FAILURE', 'LLM_FAILURE', 'DATABASE_FAILURE', 'FINANCIAL_FAILURE', 'BRIEF_FAILURE'
);
```

### Table 2: `system_status`
Holds system state for Android and Streamlit UIs. Only one active row is required.

```sql
CREATE TABLE IF NOT EXISTS jarvis_insights_schema.system_status (
    system_name VARCHAR(100) PRIMARY KEY DEFAULT 'jarvis_system',
    current_status VARCHAR(50) NOT NULL, -- 'IDLE', 'RUNNING', 'ERROR'
    last_successful_refresh TIMESTAMP WITH TIME ZONE,
    current_run_id UUID REFERENCES jarvis_insights_schema.pipeline_runs(run_id),
    signals_processed INT DEFAULT 0,
    todos_generated INT DEFAULT 0,
    financial_events_generated INT DEFAULT 0,
    fyi_generated INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 6. Target State Architectures

### Ingestion Refresh Windows
To sync with mobile client uploads, the scheduler triggers will align to:
* **06:00 AM**
* **02:00 PM**
* **09:00 PM**

### Android & Streamlit Notification Flow
* Android and Streamlit read only `system_status`.
* If `last_successful_refresh` is newer than the client's last seen timestamp:
  * Client pulls fresh data.
  * Shows local completion notification detailing metrics:
    ```text
    Jarvis Refresh Complete
    7 New Todos
    12 FYI Updates
    31 Financial Events
    Tap to Open
    ```
* Streamlit renders the pipeline runs history and stats using a live health visibility dashboard.
