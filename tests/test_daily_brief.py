# tests/test_daily_brief.py

import sys
import os
import json
from datetime import datetime, timedelta
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from storage.models.todo import Todo
from storage.models.financial_event import FinancialEvent
from storage.models.fyi_event import FyiEvent
from storage.models.daily_brief import DailyBrief
from services.signal_processor import SignalProcessor
from services.daily_brief_generator import DailyBriefGenerator


def run_daily_brief_tests():
    logger.info("Initializing database schema...")
    initialize_database()

    db = SessionLocal()
    try:
        # 1. Clean up old test data
        logger.info("Cleaning up old test data...")
        db.query(DailyBrief).delete()
        db.query(Todo).delete()
        db.query(FinancialEvent).delete()
        db.query(FyiEvent).delete()
        db.query(SignalClassification).delete()
        db.query(Signal).filter(
            Signal.summary.like("%[TEST_%")
        ).delete(synchronize_session=False)
        db.commit()

        # 2. Add mock records
        logger.info("Inserting mock signals...")
        target_date_str = "2028-06-21"
        target_date = datetime(2028, 6, 21, 12, 0, 0)
        
        # 2.1 Todo
        sig_todo = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",
            summary="[TEST_BRIEF_EXT] High priority todo due today",
            raw_json=json.dumps({"classification": "task", "due_date": "2028-06-21"}),
            created_at=target_date
        )

        # 2.2 Financial Debit
        sig_debit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_BRIEF_EXT] Rs 350.00 spent on badminton practice",
            raw_json=json.dumps({
                "amount": "350.00",
                "currency": "INR",
                "transaction_type": "debit"
            }),
            created_at=target_date
        )

        # 2.2b High-Value Financial Debit
        sig_high_debit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_BRIEF_EXT] Rs 12,000.00 spent on laptop purchase",
            raw_json=json.dumps({
                "amount": "12000.00",
                "currency": "INR",
                "transaction_type": "debit"
            }),
            created_at=target_date
        )

        # 2.3 Financial Credit
        sig_credit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_BRIEF_EXT] INR 10,000.00 credited back to bank account",
            raw_json=json.dumps({
                "amount": "10000.00",
                "currency": "INR",
                "transaction_type": "credit"
            }),
            created_at=target_date
        )

        # 2.4 FYI Event
        sig_fyi = Signal(
            source="sms",
            signal_type="delivery_update",
            category="shopping",
            importance="low",
            summary="[TEST_BRIEF_EXT] Courier delivered to your home.",
            raw_json=json.dumps({"merchant": "Amazon", "order_status": "delivered"}),
            created_at=target_date
        )

        # 2.5 Insurance Renewal (due in 3 days - should show up in Important Items)
        sig_insurance = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_BRIEF_EXT] Bike insurance renewal premium of Rs.2200 is due on 24-Jun-2028",
            raw_json=json.dumps({
                "amount": "2200.00",
                "currency": "INR",
                "due_date": "2028-06-24"
            }),
            created_at=target_date
        )

        db.add(sig_todo)
        db.add(sig_debit)
        db.add(sig_high_debit)
        db.add(sig_credit)
        db.add(sig_fyi)
        db.add(sig_insurance)
        db.commit()

        # 3. Process classifications and extractions
        logger.info("Running signal classification...")
        SignalProcessor.process_all_signals()

        logger.info("Running TODO extraction...")
        SignalProcessor.extract_todos()

        logger.info("Running financial extraction...")
        SignalProcessor.extract_financial_events()

        logger.info("Running FYI extraction...")
        SignalProcessor.extract_fyi_events()

        # 4. Generate daily brief
        logger.info("Generating daily brief...")
        brief_data = DailyBriefGenerator.generate_brief_for_date(target_date_str)

        # 5. Verify brief data
        assert len(brief_data["todos"]) == 1
        assert brief_data["todos"][0]["title"] == "[TEST_BRIEF_EXT] High priority todo due today"
        assert brief_data["todos"][0]["priority"] == "high"

        assert brief_data["financial"]["total_debit"] == 12350.0
        assert brief_data["financial"]["total_credit"] == 10000.0
        assert len(brief_data["financial"]["events"]) == 3  # debit, high debit, credit (which happened on that day)

        assert len(brief_data["fyi"]) == 1
        assert brief_data["fyi"][0]["fyi_type"] == "delivery_notification"

        # Verify Important Items (High priority todo, high value expense alert, insurance renewal due in next 7 days)
        important = brief_data["important_items"]
        assert len(important) >= 3, f"Expected at least 3 important items, got {len(important)}"
        
        # Check types inside important items
        imp_types = [item["type"] for item in important]
        assert "high_priority_todo" in imp_types
        assert "insurance_renewal" in imp_types
        assert "high_value_expense" in imp_types

        # Verify record in database
        db_brief = db.query(DailyBrief).filter(DailyBrief.date == target_date_str).first()
        assert db_brief is not None
        saved_brief = json.loads(db_brief.content_json)
        assert saved_brief["financial"]["total_credit"] == 10000.0

        # Verify overwrite handling
        logger.info("Re-generating brief to verify upsert/merge logic...")
        DailyBriefGenerator.generate_brief_for_date(target_date_str)
        briefs_count = db.query(DailyBrief).filter(DailyBrief.date == target_date_str).count()
        assert briefs_count == 1, f"Expected exactly 1 daily brief for date, got {briefs_count}"

        logger.success("ALL DAILY BRIEF GENERATOR INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"Daily Brief integration tests failed: {e}")
        try:
            # Diagnostic query
            todos_in_db = db.query(Todo).all()
            logger.error(f"Todos in database: {[{'id': t.id, 'title': t.title, 'due_date': t.due_date, 'priority': t.priority} for t in todos_in_db]}")
            if 'brief_data' in locals():
                logger.error(f"brief_data: {brief_data}")
        except Exception as diag_e:
            logger.error(f"Failed to run diagnostics: {diag_e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_daily_brief_tests()
