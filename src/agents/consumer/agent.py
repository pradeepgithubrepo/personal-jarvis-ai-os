import hashlib
import socket
import getpass
from datetime import datetime, timezone
import uuid
from supabase import Client

def clean_null_bytes(val):
    if isinstance(val, str):
        return val.replace("\u0000", "").replace("\x00", "")
    elif isinstance(val, dict):
        return {k: clean_null_bytes(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [clean_null_bytes(v) for v in val]
    return val

class ConsumerAgent:
    def __init__(self, client: Client):
        self.client = client

    def start_run(self, pipeline_name: str, phase: str, trigger_type: str, metadata: dict = None) -> uuid.UUID:
        run_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc).isoformat()
        
        # Safely get hostname and user without blocking DNS resolution in WSL
        import os
        host_name = None
        if os.path.exists("/proc/sys/kernel/hostname"):
            try:
                with open("/proc/sys/kernel/hostname", "r") as f:
                    host_name = f.read().strip()
            except Exception:
                pass
        if not host_name:
            host_name = os.environ.get("HOSTNAME") or "jarvis-wsl"
            
        user_name = os.environ.get("USER") or os.environ.get("USERNAME") or "prad"
        
        row = {
            "run_id": str(run_id),
            "pipeline_name": pipeline_name,
            "phase": phase,
            "trigger_type": trigger_type.upper(),
            "started_at": started_at,
            "status": "STARTED",
            "host_name": host_name,
            "user_name": user_name,
            "version": "v2.0.0-phase1b",
            "metadata": metadata or {}
        }
        
        self.client.table("pipeline_runs").insert(row).execute()
        
        self.log_event(
            run_id=run_id,
            severity="INFO",
            component="consumer_agent",
            event_type="RUN_STARTED",
            message=f"Pipeline run {run_id} started for {pipeline_name} ({phase})"
        )
        
        return run_id

    def log_event(self, run_id: uuid.UUID, severity: str, component: str, event_type: str, message: str, metadata: dict = None):
        event_id = uuid.uuid4()
        event_time = datetime.now(timezone.utc).isoformat()
        
        row = {
            "event_id": str(event_id),
            "run_id": str(run_id),
            "event_time": event_time,
            "severity": severity.upper(),
            "component": component,
            "event_type": event_type.upper(),
            "message": message,
            "metadata": metadata or {}
        }
        
        self.client.table("pipeline_run_events").insert(row).execute()

    def discover_files(self, bucket_name: str, folder: str) -> list[str]:
        files = self.client.storage.from_(bucket_name).list(folder)
        # Filter out folder placeholders or directory markers
        file_names = [f["name"] for f in files if f.get("name") != ".emptyFolderPlaceholder"]
        return file_names

    def download_file(self, bucket_name: str, path: str) -> bytes:
        data = self.client.storage.from_(bucket_name).download(path)
        return data

    def calculate_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def check_duplicate(self, file_hash: str) -> bool:
        res = self.client.table("processed_files").select("file_hash").eq("file_hash", file_hash).execute()
        return len(res.data) > 0

    def _normalize_signal_dict(self, signal_dict: dict) -> dict:
        file_name = (
            signal_dict.get("source_file_name") 
            or signal_dict.get("metadata", {}).get("source_file_name") 
            or ""
        )
        
        if "shobana" in file_name.lower():
            device_id = "shobana"
        else:
            device_id = "pradeep"
            
        if "signal_id" in signal_dict:
            original_sender = signal_dict.get("sender", "unknown")
            original_receiver = signal_dict.get("receiver", "unknown")
            message = signal_dict.get("content", "")
            mobile_timestamp = signal_dict.get("source_event_time")
            source_raw = (signal_dict.get("source_type") or "").lower()
            subtype_raw = (signal_dict.get("source_subtype") or "").lower()
        else:
            original_sender = signal_dict.get("sender", "unknown")
            original_receiver = signal_dict.get("deviceId", "unknown")
            message = signal_dict.get("message", "")
            timestamp_ms = signal_dict.get("timestamp")
            if timestamp_ms:
                dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
                mobile_timestamp = dt.isoformat()
            else:
                mobile_timestamp = datetime.now(timezone.utc).isoformat()
            source_raw = (signal_dict.get("source") or "").lower()
            subtype_raw = ""

        file_lower = file_name.lower()
        if "whatsapp" in source_raw or "whatsapp" in file_lower:
            source = "whatsapp"
        elif "sms" in source_raw or "sms" in file_lower:
            source = "sms"
        elif "gpay" in source_raw or "gpay" in subtype_raw or "gpay" in file_lower:
            source = "gpay"
        elif "statement" in subtype_raw or "statement" in file_lower or "bank" in file_lower:
            source = "bank_statement"
        elif "email" in file_lower:
            source = "email"
        else:
            source = source_raw or "unknown"

        metadata = signal_dict.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            
        metadata.update({
            "sender": original_sender,
            "receiver": original_receiver,
            "signal_id": signal_dict.get("signal_id"),
            "source_subtype": signal_dict.get("source_subtype") or subtype_raw,
            "source_file_name": file_name,
            "source_file_hash": signal_dict.get("source_file_hash") or metadata.get("source_file_hash"),
            "source_ingested_at": signal_dict.get("source_ingested_at") or metadata.get("source_ingested_at")
        })

        sig_str = f"{device_id}:{source}:{original_sender}:{message}:{mobile_timestamp}"
        message_hash = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()

        return {
            "device_id": device_id,
            "source": source,
            "sender": original_sender,
            "message": message,
            "mobile_timestamp": mobile_timestamp,
            "message_hash": message_hash,
            "processed": False,
            "metadata": metadata
        }

    def persist_signal(self, run_id: uuid.UUID, signal_dict: dict) -> bool:
        signal_dict = clean_null_bytes(signal_dict)
        row = self._normalize_signal_dict(signal_dict)
        message_hash = row["message_hash"]
        sender = row["sender"]
        
        try:
            self.client.table("mobile_signals").insert(row).execute()
            return True
        except Exception as e:
            err_msg = str(e)
            if "23505" in err_msg or "duplicate key" in err_msg.lower():
                self.log_event(
                    run_id=run_id,
                    severity="WARNING",
                    component="consumer_agent",
                    event_type="DUPLICATE_SIGNAL",
                    message=f"Duplicate signal skipped: {message_hash}",
                    metadata={"message_hash": message_hash, "sender": sender}
                )
                return False
            else:
                raise e

    def persist_signals_bulk(self, run_id: uuid.UUID, signals_list: list[dict]) -> int:
        if not signals_list:
            return 0
        signals_list = clean_null_bytes(signals_list)
            
        rows = []
        for signal_dict in signals_list:
            row = self._normalize_signal_dict(signal_dict)
            rows.append(row)
                
        # Deduplicate locally within the batch
        seen_hashes = set()
        unique_rows = []
        for r in rows:
            h = r["message_hash"]
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_rows.append(r)
                
        try:
            self.client.table("mobile_signals").upsert(unique_rows, on_conflict="message_hash").execute()
            return len(unique_rows)
        except Exception as e:
            # Fall back to safe sequential inserts in case upsert fails
            print(f"Bulk upsert warning (falling back to sequential): {e}")
            inserted = 0
            for row in rows:
                try:
                    self.client.table("mobile_signals").insert(row).execute()
                    inserted += 1
                except Exception as ex:
                    err_msg = str(ex)
                    if "23505" not in err_msg and "duplicate key" not in err_msg.lower():
                        raise ex
                    else:
                        self.log_event(
                            run_id=run_id,
                            severity="WARNING",
                            component="consumer_agent",
                            event_type="DUPLICATE_SIGNAL",
                            message=f"Duplicate signal skipped: {row['message_hash']}",
                            metadata={"message_hash": row['message_hash'], "sender": row['sender']}
                        )
            return inserted

    def archive_file(self, run_id: uuid.UUID, file_hash: str, file_name: str, source_type: str, bucket_name: str, from_dir: str = "incoming", to_dir: str = "archive"):
        # Insert record to processed_files for idempotency
        row = {
            "file_hash": file_hash,
            "file_name": file_name,
            "source_type": source_type,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id)
        }
        try:
            self.client.table("processed_files").upsert(row).execute()
        except Exception as e:
            err_msg = str(e)
            if "23505" not in err_msg and "duplicate key" not in err_msg.lower():
                raise e
        
        # Move file in storage
        from_path = f"{from_dir}/{file_name}" if from_dir else file_name
        to_path = f"{to_dir}/{file_name}" if to_dir else file_name
        
        try:
            self.client.storage.from_(bucket_name).move(from_path, to_path)
        except Exception as e:
            err_msg = str(e)
            if "already exists" in err_msg.lower() or "409" in err_msg:
                # File is already archived. We can safely remove it from incoming!
                try:
                    self.client.storage.from_(bucket_name).remove([from_path])
                except Exception:
                    pass
            else:
                raise e
        
        self.log_event(
            run_id=run_id,
            severity="INFO",
            component="consumer_agent",
            event_type="FILE_ARCHIVED",
            message=f"File {file_name} archived successfully",
            metadata={"file_hash": file_hash, "file_name": file_name}
        )

    def complete_run(self, run_id: uuid.UUID, metrics: dict):
        row = {
            "status": metrics.get("status", "SUCCESS"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": metrics.get("duration_ms"),
            "files_found": metrics.get("files_found", 0),
            "files_processed": metrics.get("files_processed", 0),
            "files_skipped": metrics.get("files_skipped", 0),
            "files_failed": metrics.get("files_failed", 0),
            "signals_created": metrics.get("signals_created", 0)
        }
        
        self.client.table("pipeline_runs").update(row).eq("run_id", str(run_id)).execute()
        
        self.log_event(
            run_id=run_id,
            severity="INFO",
            component="consumer_agent",
            event_type="RUN_COMPLETED",
            message=f"Pipeline run completed with status: {metrics.get('status')}",
            metadata=metrics
        )

    def fail_run(self, run_id: uuid.UUID, error_message: str, started_at: datetime = None):
        duration_ms = None
        if started_at:
            duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
            
        row = {
            "status": "FAILED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message,
            "duration_ms": duration_ms
        }
        
        self.client.table("pipeline_runs").update(row).eq("run_id", str(run_id)).execute()
        
        self.log_event(
            run_id=run_id,
            severity="CRITICAL",
            component="consumer_agent",
            event_type="RUN_FAILED",
            message=f"Pipeline run failed: {error_message}"
        )
