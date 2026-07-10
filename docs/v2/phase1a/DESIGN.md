# Phase 1A Design Document — Consumption Infrastructure

This document details the high-level architecture, contracts, and execution flow of the Jarvis V2 Consumption Infrastructure.

---

## 1. Architectural Principles & Scope

The ingestion infrastructure is designed around the **Consumer Agent Ownership** contract:
* **In Scope (Owned):** Signal Acquisition (Supabase Storage polling), Signal Persistence, SHA-256 File Deduplication, Unique Signal Deduplication, File Archiving, and Detailed Audit/Observability Logging.
* **Out of Scope (Delegated):** Qualification, classification, intent extraction, financial/school logic, and any LLM processing.

The core principle is to provide a **rock-solid ingestion framework** that acts as an idempotent pipeline before any downstream agents run.

---

## 2. Ingestion Pipeline Execution Flow

```text
       Trigger (MANUAL/SCHEDULED/RETRY/RECOVERY)
                         ↓
                   START RUN
         (Create pipeline_runs row, status = STARTED)
                         ↓
                  DISCOVER FILES
            (List bucket incoming/ files)
                         ↓
               For each discovered file:
             ┌───────────┴───────────┐
             ↓                       ↓
       DOWNLOAD FILE          FILE DUPLICATE CHECK
      (Fetch bytes)        (Check processed_files db)
             ↓                       ↓
     CALCULATE HASH           [If duplicate]
      (SHA-256 hex)          (Skip, remove from incoming)
             ↓
        PARSE JSON
     (Convert to dict)
             ↓
     PERSIST SIGNALS
     (Format signal records,
      calculate unique message_hash,
      insert to mobile_signals.
      If duplicate message_hash, log & skip)
             ↓
       ARCHIVE FILE
     (Insert into processed_files,
      move file to archive/ folder)
                         ↓
                   UPDATE METRICS
     (Calculate duration_ms, count success/fails)
                         ↓
                   COMPLETE RUN
         (Update pipeline_runs, status = SUCCESS/
          PARTIAL_SUCCESS/FAILED)
```

---

## 3. Consumer Agent Python Interface

The `ConsumerAgent` class adheres to the following interface:

```python
class ConsumerAgent:
    def __init__(self, client: Client):
        """Initializes the agent with a Supabase client."""
        pass

    def start_run(self, pipeline_name: str, phase: str, trigger_type: str, metadata: dict = None) -> uuid.UUID:
        """Creates a new pipeline_runs record and starts tracking."""
        pass

    def log_event(self, run_id: uuid.UUID, severity: str, component: str, event_type: str, message: str, metadata: dict = None):
        """Logs an event to pipeline_run_events for full observability."""
        pass

    def discover_files(self, bucket_name: str, folder: str) -> list[str]:
        """Lists files in the incoming folder of Supabase Storage."""
        pass

    def download_file(self, bucket_name: str, path: str) -> bytes:
        """Downloads the raw bytes of a file from Supabase Storage."""
        pass

    def calculate_hash(self, data: bytes) -> str:
        """Calculates the SHA-256 hash of a file's content for idempotency."""
        pass

    def check_duplicate(self, file_hash: str) -> bool:
        """Checks processed_files to verify if a file hash was processed."""
        pass

    def persist_signal(self, run_id: uuid.UUID, signal_dict: dict) -> bool:
        """Computes message_hash and inserts raw signal into mobile_signals."""
        pass

    def archive_file(self, run_id: uuid.UUID, file_hash: str, file_name: str, source_type: str, bucket_name: str):
        """Saves file hash to processed_files and moves file from incoming/ to archive/."""
        pass

    def complete_run(self, run_id: uuid.UUID, metrics: dict):
        """Updates pipeline_runs with SUCCESS or PARTIAL_SUCCESS and metrics."""
        pass

    def fail_run(self, run_id: uuid.UUID, error_message: str, started_at: datetime = None):
        """Updates pipeline_runs with FAILED status and records error."""
        pass
```

---

## 4. Idempotency & Deduplication Strategy

To prevent double-processing and ensure that pipeline runs are safe to rerun:
1. **File Level:** Every file is hashed using SHA-256 immediately upon download. If the hash is found in `processed_files`, it is deleted from the `incoming/` folder without reprocessing.
2. **Signal Level:** Each individual signal is assigned a `message_hash` computed as:
   $$\text{SHA-256}(\text{deviceId} + \text{source} + \text{sender} + \text{message} + \text{timestamp})$$
   The `mobile_signals.message_hash` column is enforced as `UNIQUE`. If the agent is rerun or duplicate signals are encountered, PostgreSQL rejects the row, and the agent logs a `DUPLICATE_SIGNAL` warning and skips it gracefully.
