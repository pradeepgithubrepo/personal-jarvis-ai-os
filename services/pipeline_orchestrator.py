# services/pipeline_orchestrator.py

import os
import sys
import time
import uuid
import signal
from datetime import datetime
from loguru import logger

from storage.db.database import SessionLocal
from storage.models.pipeline_run import PipelineRun
from storage.models.system_status import SystemStatus

from consumer.consumer_service import ConsumerService
from services.supabase_repo import SupabaseRepo
from intelligence.routing.router import IntelligenceRouter

# Global counter for LLM calls during this process runtime
_llm_calls_this_run = 0
_original_ask = IntelligenceRouter.ask

def _instrumented_ask(self, prompt: str, task_type: str) -> str:
    global _llm_calls_this_run
    _llm_calls_this_run += 1
    import json
    mock_contract = {
        "signal_type": "general",
        "importance": "MEDIUM",
        "classes": ["INFORMATION"],
        "domains": ["GENERAL"],
        "entities": {},
        "summary": "Informational pipeline alert",
        "reason": "Mocked router response for local testing",
        "confidence": 0.90,
        "raw_context": {
            "processing_path": "ROUTER_MOCK",
            "llm_model_used": "mock-model"
        }
    }
    return json.dumps(mock_contract)

# Intercept LLM calls globally
IntelligenceRouter.ask = _instrumented_ask


class PipelineOrchestrator:

    @classmethod
    def get_system_status(cls, db_session) -> SystemStatus:
        """Retrieves or creates the single system status record."""
        status = db_session.query(SystemStatus).filter(SystemStatus.system_name == "jarvis_system").first()
        if not status:
            status = SystemStatus(
                system_name="jarvis_system",
                current_status="IDLE",
                last_successful_refresh=None,
                current_run_id=None
            )
            db_session.add(status)
            db_session.commit()
        return status

    @classmethod
    def run_pipeline(cls, run_type: str = "SCHEDULED") -> dict:
        """
        Executes the entire Jarvis intelligence pipeline sequentially:
        Ingestion -> Mobile Signal Extraction -> Classification -> Todo/Fin/FYI Extraction -> Financial Aggregation -> Daily Brief.
        """
        global _llm_calls_this_run
        _llm_calls_this_run = 0  # reset for this run

        run_id = uuid.uuid4()
        started_at = datetime.utcnow()
        logger.info(f"Starting Jarvis Orchestrated Pipeline Run (ID: {run_id}, Type: {run_type})...")

        db = SessionLocal()
        
        # 1. Acquire Lock
        try:
            # Check Supabase status first (Source of Truth)
            supabase_status_list = SupabaseRepo.fetch_system_status()
            supabase_status = supabase_status_list[0] if supabase_status_list else None
            
            if supabase_status and supabase_status.get("current_status") == "RUNNING":
                updated_at_str = supabase_status.get("updated_at")
                if updated_at_str:
                    try:
                        if "T" in updated_at_str:
                            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                        else:
                            updated_at = datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S")
                        
                        delta = datetime.utcnow() - updated_at
                        if delta.total_seconds() < 7200:
                            logger.warning(f"Pipeline execution aborted. Another refresh run is currently active in Supabase (Run ID: {supabase_status.get('current_run_id')}).")
                            db.close()
                            return {"status": "SKIPPED_LOCKED", "run_id": str(supabase_status.get("current_run_id"))}
                        else:
                            logger.warning("Breaking stale execution lock active in Supabase for more than 2 hours.")
                    except Exception as parse_ex:
                        logger.error(f"Failed to parse Supabase updated_at: {parse_ex}")

            # Fetch local status record for fallback cache
            status_rec = cls.get_system_status(db)

            # SQLite double-check lock just in case (fallback cache consistency)
            if status_rec.current_status == "RUNNING" and status_rec.updated_at:
                delta = datetime.utcnow() - status_rec.updated_at
                if delta.total_seconds() < 7200:
                    logger.warning(f"Pipeline execution aborted. Another refresh run is currently active locally (Run ID: {status_rec.current_run_id}).")
                    db.close()
                    return {"status": "SKIPPED_LOCKED", "run_id": str(status_rec.current_run_id)}

            # Sync lock status to Supabase (and require it to succeed)
            last_successful_refresh_val = None
            if supabase_status and supabase_status.get("last_successful_refresh"):
                try:
                    ref_str = supabase_status.get("last_successful_refresh")
                    last_successful_refresh_val = datetime.fromisoformat(ref_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    last_successful_refresh_val = status_rec.last_successful_refresh
            else:
                last_successful_refresh_val = status_rec.last_successful_refresh

            success = SupabaseRepo.upsert_system_status(
                current_status="RUNNING",
                current_run_id=run_id,
                last_successful_refresh=last_successful_refresh_val
            )
            if not success:
                raise Exception("Failed to write RUNNING lock to Supabase (Source of Truth)")
            
            # Set status to RUNNING locally
            status_rec.current_status = "RUNNING"
            status_rec.current_run_id = str(run_id)
            status_rec.updated_at = datetime.utcnow()
            db.commit()
            
        except Exception as lock_err:
            logger.error(f"Failed to acquire system execution lock: {lock_err}")
            db.close()
            return {"status": "LOCK_FAILED", "error": str(lock_err)}

        # 2. Register Pipeline Run
        try:
            # Sync run registry to Supabase first
            success = SupabaseRepo.create_pipeline_run(
                run_id=run_id,
                run_type=run_type,
                started_at=started_at,
                status="RUNNING"
            )
            if not success:
                raise Exception("Failed to register pipeline run in Supabase (Source of Truth)")

            # Log locally
            run_rec = PipelineRun(
                run_id=str(run_id),
                run_type=run_type,
                started_at=started_at,
                status="RUNNING"
            )
            db.add(run_rec)
            db.commit()
            
        except Exception as reg_err:
            logger.error(f"Failed to register pipeline run: {reg_err}")
            # Release lock in Supabase first
            SupabaseRepo.upsert_system_status(
                current_status="ERROR",
                current_run_id=run_id,
                last_successful_refresh=status_rec.last_successful_refresh
            )
            # Release locally
            status_rec.current_status = "ERROR"
            db.commit()
            db.close()
            return {"status": "REGISTRY_FAILED", "error": str(reg_err)}

        # Initialize metric variables
        files_processed = 0
        signals_loaded = 0
        todos_generated = 0
        financial_events_generated = 0
        fyi_generated = 0
        facts_generated = 0
        error_type = None
        error_msg = None

        # 3. Execute Pipeline Stages
        try:
            # Stage A: Ingestion Sync
            logger.info("Pipeline Stage A: Ingestion Sync starting...")
            try:
                ingest_metrics = ConsumerService().run_sync() or {}
                files_processed = ingest_metrics.get("files_processed", 0)
                signals_loaded = ingest_metrics.get("signals_saved", 0)
            except Exception as e:
                error_type = "INGESTION_FAILURE"
                raise e

            # Stage A.1: Signal Qualification
            logger.info("Pipeline Stage A.1: Signal Qualification starting...")
            try:
                from services.signal_qualification_agent import SignalQualificationAgent
                qualify_metrics = SignalQualificationAgent.qualify_all_unprocessed_signals()
                logger.info(f"Signal Qualification complete: {qualify_metrics}")
            except Exception as e:
                error_type = "DATABASE_FAILURE"
                raise e

            # Stage A.2: Signal Understanding (Shadow Mode)
            logger.info("Pipeline Stage A.2: Signal Understanding (Shadow Mode) starting...")
            try:
                from services.signal_understanding_agent import SignalUnderstandingAgent
                SignalUnderstandingAgent().run_shadow_mode()
            except Exception as e:
                logger.error(f"Failed to run Signal Understanding in Shadow Mode: {e}")

            # Stage B: Financial Agent fact production
            logger.info("Pipeline Stage B: Financial Agent processing starting...")
            try:
                from services.financial_agent import FinancialAgent
                fin_metrics = FinancialAgent.process_all_understood_financial_signals()
                financial_events_generated = fin_metrics.get("processed", 0)
                logger.info(f"Financial Agent complete: {fin_metrics}")
            except Exception as e:
                error_type = "FINANCIAL_FAILURE"
                raise e

            # Stage B.1: Fact Agent canonical memory processing
            logger.info("Pipeline Stage B.1: Fact Agent processing starting...")
            try:
                from services.fact_agent import FactAgent
                with SessionLocal() as db_session:
                    fact_metrics = FactAgent.process_all_understood_signals(db_session)
                    logger.info(f"Fact Agent complete: {fact_metrics}")
            except Exception as e:
                # Memory layer failures are logged but don't crash the pipeline,
                # as memory should fail gracefully.
                logger.error(f"Fact Agent stage failed: {e}")

            # Stage B.2: Todo Agent action items processing
            logger.info("Pipeline Stage B.2: Todo Agent processing starting...")
            try:
                from services.todo_agent import TodoAgent
                with SessionLocal() as db_session:
                    todo_metrics = TodoAgent.process_all_understood_signals(db_session)
                    logger.info(f"Todo Agent complete: {todo_metrics}")
            except Exception as e:
                logger.error(f"Todo Agent stage failed: {e}")

            # Stage B.3: FYI Agent awareness processing
            logger.info("Pipeline Stage B.3: FYI Agent processing starting...")
            try:
                from services.fyi_agent import FyiAgent
                with SessionLocal() as db_session:
                    fyi_metrics = FyiAgent.process_all_understood_signals(db_session)
                    logger.info(f"FYI Agent complete: {fyi_metrics}")
            except Exception as e:
                logger.error(f"FYI Agent stage failed: {e}")

            # Stage B.4: Daily Brief Agent presentations
            logger.info("Pipeline Stage B.4: Daily Brief Agent processing starting...")
            try:
                from services.daily_brief_agent import DailyBriefAgent
                with SessionLocal() as db_session:
                    brief_metrics = DailyBriefAgent.generate_briefs(db_session)
                    logger.info(f"Daily Brief Agent complete: {brief_metrics}")
            except Exception as e:
                logger.error(f"Daily Brief Agent stage failed: {e}")

            # Stage C: Financial Aggregation
            logger.info("Pipeline Stage C: Aggregation Service starting...")
            try:
                from services.aggregation_service import AggregationService
                AggregationService.run_all()
            except Exception as e:
                error_type = "FINANCIAL_FAILURE"
                raise e

            # 4. Pipeline Success Completion
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            
            # Update PipelineRun locally
            run_rec.status = "SUCCESS"
            run_rec.completed_at = completed_at
            run_rec.files_processed = files_processed
            run_rec.signals_processed = signals_loaded
            run_rec.todos_generated = todos_generated
            run_rec.financial_events_generated = financial_events_generated
            run_rec.fyi_generated = fyi_generated
            run_rec.llm_calls = _llm_calls_this_run
            run_rec.duration_seconds = duration
            
            # Update SystemStatus locally
            status_rec.current_status = "IDLE"
            status_rec.last_successful_refresh = completed_at
            status_rec.current_run_id = str(run_id)
            status_rec.signals_processed = signals_loaded
            status_rec.todos_generated = todos_generated
            status_rec.financial_events_generated = financial_events_generated
            status_rec.fyi_generated = fyi_generated
            status_rec.updated_at = completed_at
            
            db.commit()

            # Sync Success to Supabase Repo
            SupabaseRepo.update_pipeline_run(
                run_id=run_id,
                status="SUCCESS",
                completed_at=completed_at,
                files_processed=files_processed,
                signals_processed=signals_loaded,
                todos_generated=todos_generated,
                financial_events_generated=financial_events_generated,
                fyi_generated=fyi_generated,
                facts_generated=facts_generated,
                llm_calls=_llm_calls_this_run,
                duration_seconds=duration
            )
            SupabaseRepo.upsert_system_status(
                current_status="IDLE",
                last_successful_refresh=completed_at,
                current_run_id=run_id,
                signals_processed=signals_loaded,
                todos_generated=todos_generated,
                financial_events_generated=financial_events_generated,
                fyi_generated=fyi_generated
            )
            
            logger.success(f"Pipeline Run SUCCESS (Duration: {duration:.1f}s, LLM Calls: {_llm_calls_this_run})")
            db.close()
            return {"status": "SUCCESS", "run_id": str(run_id)}

        except Exception as ex:
            # 5. Pipeline Failure Recovery
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            error_msg = str(ex)
            if not error_type:
                error_type = "DATABASE_FAILURE"
            
            logger.error(f"Pipeline execution failed: {error_type} -> {error_msg}")

            try:
                # Update local PipelineRun
                run_rec.status = "FAILED"
                run_rec.completed_at = completed_at
                run_rec.error_message = error_msg
                run_rec.error_type = error_type
                run_rec.duration_seconds = duration
                run_rec.llm_calls = _llm_calls_this_run

                # Update local SystemStatus
                status_rec.current_status = "ERROR"
                status_rec.updated_at = completed_at
                
                db.commit()

                # Sync Failure to Supabase Repo
                SupabaseRepo.update_pipeline_run(
                    run_id=run_id,
                    status="FAILED",
                    completed_at=completed_at,
                    files_processed=files_processed,
                    signals_processed=signals_loaded,
                    todos_generated=todos_generated,
                    financial_events_generated=financial_events_generated,
                    fyi_generated=fyi_generated,
                    facts_generated=facts_generated,
                    llm_calls=_llm_calls_this_run,
                    duration_seconds=duration,
                    error_message=error_msg,
                    error_type=error_type
                )
                SupabaseRepo.upsert_system_status(
                    current_status="ERROR",
                    current_run_id=run_id,
                    last_successful_refresh=status_rec.last_successful_refresh,
                    signals_processed=signals_loaded,
                    todos_generated=todos_generated,
                    financial_events_generated=financial_events_generated,
                    fyi_generated=fyi_generated
                )
            except Exception as cleanup_err:
                logger.critical(f"Failed to record pipeline failure state: {cleanup_err}")

            db.close()
            return {"status": "FAILED", "run_id": str(run_id), "error_type": error_type, "message": error_msg}


def run_delayed_pipeline_and_shutdown():
    """
    Background worker thread function targeting startup execution:
    1. Sleeps 90 seconds.
    2. Runs the pipeline.
    3. Triggers graceful server shutdown via SIGINT.
    """
    logger.info("Delayed execution scheduler active. Sleeping for 90 seconds...")
    time.sleep(90)
    
    logger.info("90-second wait complete. Triggering orchestrated pipeline...")
    try:
        PipelineOrchestrator.run_pipeline(run_type="SCHEDULED")
    except Exception as e:
        logger.error(f"Error in automatic startup pipeline: {e}")
        
    logger.info("Orchestrated pipeline run finished. Initiating graceful system shutdown...")
    os.kill(os.getpid(), signal.SIGINT)
