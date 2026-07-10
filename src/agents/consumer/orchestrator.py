import json
import time
from datetime import datetime, timezone
import uuid
from supabase import Client
from src.agents.consumer.agent import ConsumerAgent

# Import Collectors
from src.agents.consumer.collectors.whatsapp_collector import collect_whatsapp
from src.agents.consumer.collectors.sms_collector import collect_sms
from src.agents.consumer.collectors.gpay_collector import collect_gpay
from src.agents.consumer.collectors.bank_statement_collector import collect_bank_statement

def run_pipeline(client: Client, trigger_type: str = "MANUAL") -> dict:
    agent = ConsumerAgent(client)
    started_at = datetime.now(timezone.utc)
    
    # START RUN
    try:
        run_id = agent.start_run(
            pipeline_name="consumer_sync",
            phase="phase1b",
            trigger_type=trigger_type
        )
    except Exception as e:
        print(f"Error starting pipeline run: {e}")
        return {
            "status": "FAILED",
            "error_message": f"Could not connect to Supabase to start run: {str(e)}",
            "files_found": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "signals_created": 0,
            "duration_ms": 0
        }

    metrics = {
        "status": "SUCCESS",
        "files_found": 0,
        "files_processed": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "signals_created": 0,
        "duration_ms": 0
    }
    
    bucket_name = "jarvis-signals"
    
    try:
        # 1. Run WhatsApp Collector
        m_wa = collect_whatsapp(client, run_id, bucket_name)
        
        # 2. Run SMS Collector
        m_sms = collect_sms(client, run_id, bucket_name)
        
        # 3. Run GPay Collector
        m_gpay = collect_gpay(client, run_id, bucket_name)
        
        # 4. Run Bank Statement Collector
        m_stmt = collect_bank_statement(client, run_id, bucket_name)
        
        # 5. Process files in root incoming folder (legacy Phase 1A compatibility)
        root_folder = "incoming"
        root_files = agent.discover_files(bucket_name, root_folder)
        
        for name in root_files:
            if name in ["whatsapp", "sms", "gpay", "statements", "failed", "archive", "daily_briefs"]:
                continue
            if not name.endswith(".json"):
                continue
                
            path = f"{root_folder}/{name}"
            agent.log_event(
                run_id=run_id,
                severity="INFO",
                component="consumer_agent",
                event_type="FILE_DISCOVERED",
                message=f"Discovered root file: {path}"
            )
            
            try:
                data = agent.download_file(bucket_name, path)
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_DOWNLOAD_FAILED",
                    message=f"Failed to download {path}: {str(e)}"
                )
                continue
                
            file_hash = agent.calculate_hash(data)
            if agent.check_duplicate(file_hash):
                metrics["files_skipped"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="INFO",
                    component="consumer_agent",
                    event_type="DUPLICATE_FILE",
                    message=f"Duplicate file skipped: {name}"
                )
                try:
                    client.storage.from_(bucket_name).remove([path])
                except Exception:
                    pass
                continue
                
            try:
                content = json.loads(data.decode("utf-8"))
                signals = content.get("signals", [])
                for sig in signals:
                    sig["source_file_name"] = name
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_PARSE_FAILED",
                    message=f"Failed to parse JSON file {name}: {str(e)}"
                )
                try:
                    client.storage.from_(bucket_name).move(path, f"failed/{name}")
                except Exception:
                    pass
                continue
                
            signals_created_file = agent.persist_signals_bulk(run_id, signals)
            metrics["signals_created"] += signals_created_file
                    
            try:
                agent.archive_file(run_id, file_hash, name, "legacy", bucket_name, root_folder, "archive")
                metrics["files_processed"] += 1
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_ARCHIVE_FAILED",
                    message=f"Failed to archive file {name}: {str(e)}"
                )
                
        # Aggregate all metrics
        metrics["files_processed"] += m_wa["files_processed"] + m_sms["files_processed"] + m_gpay["files_processed"] + m_stmt["files_processed"]
        metrics["files_skipped"] += m_wa["files_skipped"] + m_sms["files_skipped"] + m_gpay["files_skipped"] + m_stmt["files_skipped"]
        metrics["files_failed"] += m_wa["files_failed"] + m_sms["files_failed"] + m_gpay["files_failed"] + m_stmt["files_failed"]
        metrics["signals_created"] += m_wa["signals_created"] + m_sms["signals_created"] + m_gpay["signals_created"] + m_stmt["signals_created"]
        metrics["files_found"] = metrics["files_processed"] + metrics["files_skipped"] + metrics["files_failed"]
        
        # Determine overall status
        if metrics["files_failed"] > 0:
            if metrics["files_processed"] > 0 or metrics["files_skipped"] > 0:
                metrics["status"] = "PARTIAL_SUCCESS"
            else:
                metrics["status"] = "FAILED"
        else:
            metrics["status"] = "SUCCESS"
            
        metrics["duration_ms"] = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        agent.complete_run(run_id, metrics)
        
    except Exception as e:
        metrics["status"] = "FAILED"
        agent.fail_run(run_id, str(e), started_at)
        
    return metrics
