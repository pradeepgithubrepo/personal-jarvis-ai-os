# TODO AGENT WALKTHROUGH
**Jarvis V1 To-Do Agent Backend Implementation Walkthrough**

---

## 1. Database Schema Migrations

We created a structured migration file [phase3a_todo_agent.sql](file:///home/prad/petprojects/ai/jarvis/sql/migrations/phase3a_todo_agent.sql) to set up the tasks schemas:
* Custom Postgres enums: `task_status` (`OPEN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`), `task_priority` (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), `task_source_type` (`AUTO_GENERATED`, `USER_TEXT`, `USER_VOICE`), `task_created_by` (`JARVIS`, `USER`).
* Columns `assigned_to` and `notification_profile` are integrated for multi-user assignment and flexible alarm offsets.
* Foreign key constraint `route_id REFERENCES signal_routes(id)` maps task lineage to routing decisions.

---

## 2. To-Do Agent Implementation (`todo_agent.py`)

The real `TodoAgent` has been implemented in [todo_agent.py](file:///home/prad/petprojects/ai/jarvis/src/agents/todo/todo_agent.py).

### Core Features

1. **Reasoning Prompts**:
   Instructs the local LLM (`qwen2.5:1.5b`) to evaluate the incoming raw signal message, classify it, rewrite the title into an imperative action format, and assign priority and notification profile levels.
2. **Deduplication Hook**:
   Fetches currently `OPEN` and `IN_PROGRESS` tasks from Supabase and passes them to the LLM context. The LLM decides if the incoming signal represents a new task (`CREATE_TASK`), a duplicate to merge (`MERGE_WITH_EXISTING`), or should be skipped (`IGNORE`).
3. **Traceability Insertion**:
   For auto-generated tasks, the record stores `route_id`, enabling complete lineage tracing.
4. **Fallback Handler**:
   If the LLM output fails to parse or return valid JSON, the agent automatically triggers a deterministic fallback, creating the task safely using the underlying contract parameters.

---

## 3. Worker Execution & Pipeline Integration

We implemented two entry points for executing the worker:

1. **Standalone CLI Ingestion Worker**:
   [run_todo_agent.py](file:///home/prad/petprojects/ai/jarvis/scripts/run_todo_agent.py) triggers pulling pending routes, running LLM checks, and updating Supabase states.
2. **Orchestrated Backfill Pipeline**:
   Modified [run_pipeline_backfill.py](file:///home/prad/petprojects/ai/jarvis/scripts/run_pipeline_backfill.py) to automatically execute the `TodoAgent` ingestion worker at the end of the backfill process.

---

## 4. Verification

To verify that the To-Do Agent operates correctly, execute the following validation steps:

1. **Database Migration**:
   Confirm the `tasks` table exists on Supabase.
2. **Backfill Execution**:
   Run the integrated backfill pipeline:
   ```bash
   .venv/bin/python scripts/run_pipeline_backfill.py
   ```
   This will qualify, route, and ingest tasks, running the local LLM reasoning model for all ACTION routes.
3. **Task Verification**:
   Query the Supabase database to verify that tasks are successfully created in the `tasks` table with clean imperatives (e.g. *"Pay TNEB Electricity Bill"*) and correct `route_id` references.
