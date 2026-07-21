"""
tests/test_master_daily_pipeline.py

Unit & Integration Test Suite for Master Daily Pipeline Orchestrator.
"""
import unittest
from unittest.mock import MagicMock, patch

from scripts.run_master_daily_pipeline import run_master_pipeline


class TestMasterDailyPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()

    @patch("scripts.run_master_daily_pipeline.run_consumer_pipeline")
    @patch("scripts.run_master_daily_pipeline.SignalQualificationAgent")
    @patch("scripts.run_master_daily_pipeline.run_sua_pipeline")
    @patch("scripts.run_master_daily_pipeline.SignalRouter")
    @patch("scripts.run_master_daily_pipeline.ContractDispatcher")
    @patch("scripts.run_master_daily_pipeline.TodoAgent")
    @patch("scripts.run_master_daily_pipeline.LifecycleAgent")
    @patch("scripts.run_master_daily_pipeline.DailyBriefingAgent")
    def test_run_master_pipeline_full_chain(
        self,
        mock_briefing_class,
        mock_lifecycle_class,
        mock_todo_class,
        mock_dispatcher_class,
        mock_router_class,
        mock_sua_fn,
        mock_qual_class,
        mock_consumer_fn,
    ):
        # Setup Stage 1 Mock
        mock_consumer_fn.return_value = {
            "status": "SUCCESS",
            "files_processed": 3,
            "signals_created": 5,
        }

        # Setup Stage 2 Mock (Unprocessed mobile signals)
        mock_unproc = MagicMock()
        mock_unproc.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": "sig-1",
                "source": "sms",
                "sender": "HDFCBK",
                "message": "Paid Rs 500",
                "mobile_timestamp": "2026-07-21T10:00:00Z",
                "device_id": "dev-1",
                "message_hash": "hash-1",
            }
        ]
        self.mock_client.table.return_value = mock_unproc

        mock_qual_agent = mock_qual_class.return_value
        mock_qual_agent.qualify_signal.return_value = {
            "status": "QUALIFIED",
            "score": 90,
            "reason": "Financial transaction",
            "canonical_metadata": {},
            "amount": 500.0,
            "currency": "INR",
            "transaction_type": "EXPENSE",
        }

        # Setup Stage 3 Mock
        mock_sua_fn.return_value = {
            "status": "SUCCESS",
            "signals_processed": 1,
            "signals_understood": 1,
        }

        # Setup Stage 4 Mock
        mock_router = mock_router_class.return_value
        mock_dispatcher = mock_dispatcher_class.return_value

        # Setup Stage 5 Mock
        mock_todo = mock_todo_class.return_value

        # Setup Stage 6 Mock
        mock_life = mock_lifecycle_class.return_value
        mock_life.process_active_items.return_value = {"status": "SUCCESS", "promoted_count": 1}

        # Setup Stage 7 Mock
        mock_briefing = mock_briefing_class.return_value
        mock_briefing.generate_daily_briefing.return_value = {"status": "SUCCESS"}

        # Execute master pipeline
        summary = run_master_pipeline(self.mock_client, trigger_type="SCHEDULED")

        # Assertions
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(len(summary["failed_stages"]), 0)
        self.assertEqual(summary["stage_results"]["stage1_consumer"]["signals_created"], 5)
        self.assertEqual(summary["stage_results"]["stage2_qualification"]["qualified_count"], 1)
        self.assertEqual(summary["stage_results"]["stage3_sua"]["signals_understood"], 1)

        # Verify invocations across all 7 stages
        mock_consumer_fn.assert_called_once()
        mock_sua_fn.assert_called_once()
        mock_life.process_active_items.assert_called_once()
        mock_briefing.generate_daily_briefing.assert_called_once()


if __name__ == "__main__":
    unittest.main()
