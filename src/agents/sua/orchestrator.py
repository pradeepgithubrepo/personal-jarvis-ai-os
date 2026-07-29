import time
from datetime import datetime, timezone
import uuid
from supabase import Client
from loguru import logger

from src.agents.sua.agent import SignalUnderstandingAgent

def run_pipeline(client: Client, trigger_type: str = "MANUAL", model_name: str = None) -> dict:
    started_at = datetime.now(timezone.utc)
    run_id = uuid.uuid4()
    
    # 1. Start pipeline run log
    # We will log to pipeline_runs table under jarvis_insights_schemav1
    # Get host and user details safely
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
    
    run_row = {
        "run_id": str(run_id),
        "pipeline_name": "sua_sync",
        "phase": "phase2a",
        "trigger_type": trigger_type.upper(),
        "started_at": started_at.isoformat(),
        "status": "STARTED",
        "host_name": host_name,
        "user_name": user_name,
        "version": "v2.0.0-phase2a",
        "metadata": {}
    }
    
    metrics = {
        "status": "SUCCESS",
        "signals_processed": 0,
        "signals_understood": 0,
        "signals_failed": 0,
        "duration_ms": 0
    }
    
    def log_event(severity: str, event_type: str, message: str, metadata: dict = None):
        event_id = uuid.uuid4()
        event_time = datetime.now(timezone.utc).isoformat()
        try:
            client.table("pipeline_run_events").insert({
                "event_id": str(event_id),
                "run_id": str(run_id),
                "event_time": event_time,
                "severity": severity.upper(),
                "component": "sua_orchestrator",
                "event_type": event_type.upper(),
                "message": message,
                "metadata": metadata or {}
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    try:
        client.table("pipeline_runs").insert(run_row).execute()
        log_event("INFO", "RUN_STARTED", f"SUA Pipeline run {run_id} started")
    except Exception as e:
        logger.error(f"Error starting pipeline run: {e}")
        return {
            "status": "FAILED",
            "error_message": f"Could not connect to Supabase to start run: {str(e)}",
            "signals_processed": 0,
            "signals_understood": 0,
            "signals_failed": 0,
            "duration_ms": 0
        }
        
    try:
        # 2. Get qualified signals that don't have understood signals yet (Delta processing)
        # Using nested select to filter out already understood signals
        res = client.table("qualified_signals").select("*, understood_signals(id)").execute()
        
        qualified_signals = []
        for row in res.data:
            if row.get("qualification_status") != "QUALIFIED":
                continue
            # If understood_signals is empty list/dict/None, it needs processing
            us = row.get("understood_signals")
            if not us:
                qualified_signals.append(row)
                
        metrics["signals_processed"] = len(qualified_signals)
        log_event("INFO", "DELTA_DISCOVERED", f"Discovered {len(qualified_signals)} new qualified signals for processing")
        
        sua = SignalUnderstandingAgent(client, model_name=model_name)
        
        understood_rows = []
        for sig in qualified_signals:
            try:
                # Classify and understand
                understood = sua.understand_signal(sig)
                
                # Construct understood_signals row
                row_data = {
                    "id": str(uuid.uuid4()),
                    "qualified_signal_id": sig["id"],
                    "raw_signal_id": sig["signal_id"],
                    "device_id": sig.get("device_id"),
                    "message_hash": sig.get("message_hash"),
                    "metadata": {**(sig.get("metadata") or {}), **(understood.get("metadata") or {})},
                    "signal_type": understood["signal_type"],
                    "importance": understood["importance"],
                    "confidence": understood["confidence"],
                    "summary": understood["summary"],
                    "reason": understood["reason"],
                    "processing_path": understood["processing_path"],
                    "llm_model_used": understood["llm_model_used"],
                    "contract_json": understood["contract_json"],
                    "is_verified": False
                }
                
                # Insert individually to allow partial success and capture errors
                client.table("understood_signals").insert(row_data).execute()
                metrics["signals_understood"] += 1
                
            except Exception as e:
                metrics["signals_failed"] += 1
                log_event("ERROR", "SIGNAL_PROCESSING_FAILED", f"Failed to process signal {sig.get('id')}: {str(e)}", {
                    "qualified_signal_id": sig.get("id"),
                    "error": str(e)
                })
                
        duration = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        metrics["duration_ms"] = duration
        
        # Complete run
        client.table("pipeline_runs").update({
            "status": "SUCCESS",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration,
            "metadata": metrics
        }).eq("run_id", str(run_id)).execute()
        
        log_event("INFO", "RUN_COMPLETED", f"SUA Pipeline run completed with status: SUCCESS", metrics)
        
    except Exception as e:
        logger.error(f"SUA Pipeline execution failed: {e}")
        duration = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        metrics["status"] = "FAILED"
        metrics["duration_ms"] = duration
        
        try:
            client.table("pipeline_runs").update({
                "status": "FAILED",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration,
                "error_message": str(e)
            }).eq("run_id", str(run_id)).execute()
            log_event("CRITICAL", "RUN_FAILED", f"SUA Pipeline run failed: {str(e)}")
        except Exception as ex:
            logger.error(f"Failed to update failed run status: {ex}")
            
    return metrics
