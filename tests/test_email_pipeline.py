# tests/test_email_pipeline.py

import sys
import os
from loguru import logger
from unittest.mock import patch, MagicMock

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.task import Task
from services.email_pipeline import EmailPipeline
from storage.repositories.signal_repository import SignalRepository


def run_pipeline_test():
    logger.info("Initializing database and schema...")
    initialize_database()

    import datetime
    start_time = datetime.datetime.utcnow()

    db = SessionLocal()
    try:
        # Clear existing test data
        db.query(Signal).filter(Signal.summary.like("%[TEST_PIPELINE]%")).delete(synchronize_session=False)
        db.query(Signal).filter(Signal.message_id.in_(["msg_email_finance_123", "msg_email_noise_456", "msg_email_otp_789", "msg_email_school_999"])).delete(synchronize_session=False)
        db.query(Task).filter(Task.title.like("%[TEST_PIPELINE]%")).delete(synchronize_session=False)
        db.commit()

        # Define mock unread emails
        mock_emails = [
            # 1. Finance alert
            {
                "id": "msg_email_finance_123",
                "account": "test_account",
                "subject": "[TEST_PIPELINE] ALERT: HDFC Bank Credit Card spend of INR 650.00 to merchant Zomato from card ending 3221",
                "sender": "alerts@hdfcbank.com",
                "snippet": "Transaction alert of INR 650.00 spent on UPI VPA 174975690734@hdfcbank (HAJNOOL AKBAR S)",
                "body": "Dear Customer, your card ending 3221 was debited INR 650.00. VPA is 174975690734@hdfcbank (HAJNOOL AKBAR S). Ref txn: 998877",
            },
            # 2. General newsletter (noise)
            {
                "id": "msg_email_noise_456",
                "account": "test_account",
                "subject": "[TEST_PIPELINE] Weekly Newsletter from Substack",
                "sender": "news@substack.com",
                "snippet": "Here are the top stories of the week.",
                "body": "Check out these recommended posts...",
            },
            # 3. OTP email (noise)
            {
                "id": "msg_email_otp_789",
                "account": "test_account",
                "subject": "[TEST_PIPELINE] Your login OTP code",
                "sender": "security@bank.com",
                "snippet": "Use code 9988 to verify your identity.",
                "body": "Your one-time password is 9988. Do not share it.",
            },
            # 4. School Task email
            {
                "id": "msg_email_school_999",
                "account": "test_account",
                "subject": "[TEST_PIPELINE] Science homework model assignment",
                "sender": "homework@school.com",
                "snippet": "Homework assignment science project due next Monday.",
                "body": "Hi parents, please help kids to submit the science model homework by next Monday.",
            }
        ]

        # Mock Gmail authentication and reading
        with patch("services.email_pipeline.GmailClient") as MockGmailClient, \
             patch("services.email_pipeline.EmailReader") as MockEmailReader:
            
            mock_gmail_instance = MagicMock()
            MockGmailClient.return_value = mock_gmail_instance
            mock_gmail_instance.authenticate_all_accounts.return_value = ["dummy_service"]

            mock_reader_instance = MagicMock()
            MockEmailReader.return_value = mock_reader_instance
            mock_reader_instance.fetch_unread_emails.return_value = mock_emails

            logger.info("Running Email Pipeline with mocked emails...")
            pipeline = EmailPipeline()
            pipeline.run()

        # Re-fetch from DB to verify states
        db.expire_all()

        # Verify OTP filtering: msg_email_otp_789 should be marked as "ignore"
        otp_sig = db.query(Signal).filter(Signal.message_id == "msg_email_otp_789").first()
        assert otp_sig is not None, "OTP email should have been saved with an ignore/noise marker"
        assert otp_sig.importance == "ignore", f"Expected 'ignore' importance for OTP, got {otp_sig.importance}"
        
        # Verify noise filtering: msg_email_noise_456 should be marked as "ignore"
        noise_sig = db.query(Signal).filter(Signal.message_id == "msg_email_noise_456").first()
        assert noise_sig is not None, "Noise email should have been saved with an ignore/noise marker"
        assert noise_sig.importance == "ignore", f"Expected 'ignore' importance for noise, got {noise_sig.importance}"
        logger.success("OTP and General noise suppression verified!")

        # Verify finance signal extraction
        finance_sig = db.query(Signal).filter(Signal.message_id == "msg_email_finance_123").first()
        assert finance_sig is not None, "Finance email should have been processed and saved"
        assert finance_sig.category == "finance", f"Expected 'finance' category, got {finance_sig.category}"
        assert finance_sig.signal_type == "financial_transaction", f"Expected 'financial_transaction' signal type, got {finance_sig.signal_type}"
        
        # Verify school task update extraction and task creation
        school_sig = db.query(Signal).filter(Signal.message_id == "msg_email_school_999").first()
        assert school_sig is not None, "School email should have been processed and saved"
        assert school_sig.category == "education", f"Expected 'education' category, got {school_sig.category}"
        assert school_sig.importance == "high", f"Expected high importance for school updates, got {school_sig.importance}"
        
        import json
        school_details = json.loads(school_sig.raw_json)
        assert "classification" in school_details, "Expected classification inside school details"
        assert school_details["classification"] in ("task", "FYI"), f"Expected task or FYI classification, got {school_details['classification']}"
        
        # Check task creation in tasks table
        if school_details["classification"] == "task":
            created_task = db.query(Task).filter(Task.title.like("%Science homework%")).first()
            assert created_task is not None, "Expected a task to be created for school task notification"
            logger.success("School task creation verified successfully!")
        else:
            logger.success("School FYI classification verified successfully!")

        logger.success("School update classification and priority verified!")

        # Test Cross-Channel Deduplication: Run again with duplicate finance details on a different message ID
        # If we try to ingest the same finance transaction, it should be skipped
        duplicate_email = {
            "id": "msg_email_finance_duplicate",
            "account": "test_account2",
            "subject": "Fwd: [TEST_PIPELINE] ALERT: HDFC Bank Credit Card spend of INR 650.00 to merchant Zomato from card ending 3221",
            "sender": "spouse@family.com",
            "snippet": "Transaction alert of INR 650.00 spent on UPI VPA 174975690734@hdfcbank (HAJNOOL AKBAR S)",
            "body": "Dear Customer, your card ending 3221 was debited INR 650.00. VPA is 174975690734@hdfcbank (HAJNOOL AKBAR S). Ref txn: 998877",
        }

        # Let's verify is_duplicate_signal directly first
        finance_details = json.loads(finance_sig.raw_json)
        is_dup = SignalRepository.is_duplicate_signal("finance", "financial_transaction", finance_details, finance_sig.summary)
        assert is_dup is True, "Expected identical transaction to be detected as a duplicate"
        logger.success("Direct transaction ID/amount cross-channel deduplication verified!")

        logger.success("ALL EMAIL PIPELINE AND CROSS-CHANNEL INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"Email pipeline integration test failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_pipeline_test()
