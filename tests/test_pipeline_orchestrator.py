# tests/test_pipeline_orchestrator.py

import sys
import os
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.pipeline_run import PipelineRun
from storage.models.system_status import SystemStatus
from services.pipeline_orchestrator import PipelineOrchestrator


def run_orchestrator_tests():
    logger.info("Initializing database for orchestrator tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clean up old status/runs
        db.query(SystemStatus).filter(SystemStatus.system_name == "jarvis_system").delete()
        db.query(PipelineRun).delete()
        db.commit()

        # Mock all pipeline execution stages so we don't hit the LLM/External services
        mock_consumer = MagicMock()
        mock_consumer.return_value.run_sync.return_value = {"files_processed": 2, "signals_saved": 5}

        mock_mobile_pipeline = MagicMock()
        mock_email_pipeline = MagicMock()
        
        mock_signal_processor = MagicMock()
        mock_signal_processor.extract_todos.return_value = 3
        mock_signal_processor.extract_financial_events.return_value = 2
        mock_signal_processor.extract_fyi_events.return_value = 4

        mock_fin_service = MagicMock()
        mock_brief_gen = MagicMock()

        # Mock Supabase Repo methods to prevent outbound calls during tests
        mock_supabase_repo = MagicMock()

        # Gather patches
        patches = [
            patch("services.pipeline_orchestrator.ConsumerService", mock_consumer),
            patch("services.pipeline_orchestrator.MobileSignalPipeline", mock_mobile_pipeline),
            patch("services.pipeline_orchestrator.EmailPipeline", mock_email_pipeline),
            patch("services.pipeline_orchestrator.SignalProcessor", mock_signal_processor),
            patch("services.pipeline_orchestrator.FinancialIntelligenceService", mock_fin_service),
            patch("services.pipeline_orchestrator.DailyBriefGenerator", mock_brief_gen),
            patch("services.pipeline_orchestrator.SupabaseRepo", mock_supabase_repo)
        ]

        # Apply patches
        for p in patches:
            p.start()

        try:
            # Test Case 1: Standard Successful Run
            logger.info("Test Case 1: Standard successful pipeline execution...")
            result = PipelineOrchestrator.run_pipeline(run_type="SCHEDULED")
            
            assert result["status"] == "SUCCESS", f"Expected SUCCESS, got {result['status']}"
            run_id = result["run_id"]
            logger.success("Test Case 1: Successful status returned.")

            # Verify local SQLite status & runs
            db.expire_all()
            status_rec = db.query(SystemStatus).filter(SystemStatus.system_name == "jarvis_system").first()
            assert status_rec is not None
            assert status_rec.current_status == "IDLE", f"Expected status IDLE, got {status_rec.current_status}"
            assert status_rec.current_run_id == run_id
            assert status_rec.signals_processed == 5
            
            run_rec = db.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
            assert run_rec is not None
            assert run_rec.status == "SUCCESS"
            assert run_rec.files_processed == 2
            assert run_rec.signals_processed == 5
            logger.success("Test Case 1: Local SQLite records verified.")

            # Verify SupabaseRepo calls
            mock_supabase_repo.create_pipeline_run.assert_called_once()
            mock_supabase_repo.upsert_system_status.assert_called()
            mock_supabase_repo.update_pipeline_run.assert_called_once()
            logger.success("Test Case 1: Supabase repo sync calls verified.")

            # Reset mocks for next test
            mock_supabase_repo.reset_mock()

            # Test Case 2: Concurrent Lock Rejection
            logger.info("Test Case 2: Concurrent execution lock testing...")
            # Set status to RUNNING manually to simulate concurrent active run
            status_rec.current_status = "RUNNING"
            status_rec.updated_at = datetime.utcnow()
            db.commit()

            concurrent_result = PipelineOrchestrator.run_pipeline(run_type="ADHOC")
            assert concurrent_result["status"] == "SKIPPED_LOCKED", f"Expected SKIPPED_LOCKED, got {concurrent_result['status']}"
            assert concurrent_result["run_id"] == run_id
            logger.success("Test Case 2: Concurrent execution rejected as locked.")

            # Test Case 3: Pipeline Stage Failure handling
            logger.info("Test Case 3: Pipeline stage failure handling...")
            # Reset status to IDLE
            status_rec.current_status = "IDLE"
            db.commit()

            # Make MobileSignalPipeline run throw an error
            mock_mobile_pipeline.return_value.run.side_effect = Exception("Ollama connection failed")

            failure_result = PipelineOrchestrator.run_pipeline(run_type="SCHEDULED")
            assert failure_result["status"] == "FAILED", f"Expected FAILED, got {failure_result['status']}"
            assert failure_result["error_type"] == "LLM_FAILURE", f"Expected LLM_FAILURE, got {failure_result['error_type']}"
            
            # Verify lock is released to ERROR status
            db.expire_all()
            status_rec = db.query(SystemStatus).filter(SystemStatus.system_name == "jarvis_system").first()
            assert status_rec.current_status == "ERROR", f"Expected status to be ERROR after failure, got {status_rec.current_status}"

            # Verify failure record in SQLite
            fail_run_rec = db.query(PipelineRun).filter(PipelineRun.run_id == failure_result["run_id"]).first()
            assert fail_run_rec is not None
            assert fail_run_rec.status == "FAILED"
            assert fail_run_rec.error_type == "LLM_FAILURE"
            assert "Ollama connection failed" in fail_run_rec.error_message
            logger.success("Test Case 3: Stage failure recorded and locked status released cleanly.")

        finally:
            # Stop all patches
            for p in patches:
                p.stop()

        logger.success("ALL PIPELINE ORCHESTRATOR TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_orchestrator_tests()
