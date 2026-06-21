# tests/test_supabase_sync.py

import sys
import os
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.daily_brief import DailyBrief
from services.daily_brief_generator import DailyBriefGenerator
from services.supabase_sync_service import SupabaseSyncService


def run_supabase_sync_tests():
    logger.info("Initializing database for sync tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clean up old test briefs
        target_date_str = "2028-06-21"
        db.query(DailyBrief).filter(DailyBrief.date == target_date_str).delete()
        db.commit()

        # Add a mock DailyBrief in SQLite
        mock_content = {
            "todos": [{"id": 1, "title": "Test todo", "due_date": target_date_str, "priority": "high"}],
            "financial": {"total_debit": 100.0, "total_credit": 200.0, "events": []},
            "fyi": [],
            "important_items": []
        }
        brief_obj = DailyBrief(
            date=target_date_str,
            content_json=json.dumps(mock_content)
        )
        db.add(brief_obj)
        db.commit()

        # Test Case 1: Successful Upload
        logger.info("Test Case 1: Verifying successful sync upload...")
        with patch("consumer.supabase_client.SupabaseClient.upload_file") as mock_upload:
            mock_upload.return_value = True
            
            success = SupabaseSyncService.sync_brief_for_date(target_date_str)
            
            assert success is True, "Expected sync_brief_for_date to return True on success."
            mock_upload.assert_called_once()
            
            # Verify upload path and content
            called_args, called_kwargs = mock_upload.call_args
            assert called_args[0] == f"daily_briefs/{target_date_str}.json"
            uploaded_json = json.loads(called_args[1])
            assert uploaded_json["todos"][0]["title"] == "Test todo"
            logger.success("Test Case 1: Passed successfully.")

        # Test Case 2: Failed Upload (Returns False)
        logger.info("Test Case 2: Verifying failed upload handling...")
        with patch("consumer.supabase_client.SupabaseClient.upload_file") as mock_upload:
            mock_upload.return_value = False
            
            success = SupabaseSyncService.sync_brief_for_date(target_date_str)
            
            assert success is False, "Expected sync_brief_for_date to return False when upload fails."
            logger.success("Test Case 2: Passed successfully.")

        # Test Case 3: Network Exception (Should be caught and handled gracefully)
        logger.info("Test Case 3: Verifying network exception handling...")
        with patch("consumer.supabase_client.SupabaseClient.upload_file") as mock_upload:
            mock_upload.side_effect = Exception("Network connection timeout")
            
            # The function should NOT raise an exception, but return False
            try:
                success = SupabaseSyncService.sync_brief_for_date(target_date_str)
                assert success is False, "Expected sync_brief_for_date to return False when exception is raised."
                logger.success("Test Case 3: Passed successfully (exception caught gracefully).")
            except Exception as e:
                logger.error(f"Test Case 3 failed: Exception was raised instead of being caught: {e}")
                raise e

        # Test Case 4: End-to-End Trigger via DailyBriefGenerator
        logger.info("Test Case 4: Verifying end-to-end sync trigger via DailyBriefGenerator...")
        with patch("services.supabase_sync_service.SupabaseSyncService.sync_brief_for_date") as mock_sync:
            # We mock the generate dependencies to return a basic dictionary
            # and verify sync_brief_for_date is triggered.
            mock_sync.return_value = True
            
            # Trigger brief generation
            # Note: since this might query other tables, we can patch other parts or query locally.
            # Let's just patch the sync service method and check if it is called.
            with patch("storage.models.todo.Todo"), patch("storage.models.financial_event.FinancialEvent"), patch("storage.models.fyi_event.FyiEvent"):
                DailyBriefGenerator.generate_brief_for_date(target_date_str)
                mock_sync.assert_called_with(target_date_str)
                logger.success("Test Case 4: Passed successfully (sync triggered end-to-end).")

        logger.success("ALL SUPABASE SYNC INTEGRATION TESTS PASSED SUCCESSFULLY!")

    finally:
        # Clean up
        db.query(DailyBrief).filter(DailyBrief.date == "2028-06-21").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_supabase_sync_tests()
