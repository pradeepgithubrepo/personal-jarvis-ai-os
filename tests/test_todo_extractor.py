# tests/test_todo_extractor.py

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
from storage.models.task import Task
from storage.models.todo import Todo
from services.signal_processor import SignalProcessor


def run_todo_extractor_tests():
    logger.info("Initializing database schema...")
    initialize_database()

    db = SessionLocal()
    try:
        # 1. Clean up old test data
        logger.info("Cleaning up old test data...")
        db.query(Todo).delete()
        db.query(SignalClassification).delete()
        db.query(Signal).filter(
            (Signal.summary.like("%[TEST_TODO_EXT]%")) | (Signal.summary.like("%[TEST_SIG_PROC]%"))
        ).delete(synchronize_session=False)
        db.query(Task).filter(
            (Task.title.like("%[TEST_TODO_EXT]%")) | (Task.title.like("%[TEST_SIG_PROC]%"))
        ).delete(synchronize_session=False)
        db.commit()

        # 2. Add mock signals
        logger.info("Inserting mock TODO signals...")
        base_time = datetime(2026, 6, 21, 12, 0, 0)

        # Case 1: WhatsApp personal todo with "tomorrow" keyword
        sig_tomorrow = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",
            summary="[TEST_TODO_EXT] Bring a Father's Day greeting card tomorrow",
            raw_json=json.dumps({"classification": "task"}),
            created_at=base_time
        )

        # Case 2: School homework with explicit DD-MM-YYYY date format
        sig_date_pattern = Signal(
            source="whatsapp",
            signal_type="school_update",
            category="education",
            importance="high",
            summary="[TEST_TODO_EXT] Submit science project homework by 28-06-2026",
            raw_json=json.dumps({"classification": "task"}),
            created_at=base_time
        )

        # Case 3: Actionable items inheriting due_date from tasks table (or details)
        sig_task_inherit = Signal(
            source="sms",
            signal_type="important",
            category="general",
            importance="medium",
            summary="[TEST_TODO_EXT] Renew car insurance policy",
            raw_json=json.dumps({"due_date": "2026-07-06"}),
            created_at=base_time
        )
        
        # Case 4: Named date text (e.g. "28 Jun")
        sig_named_date = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",
            summary="[TEST_TODO_EXT] Book flight tickets by 28 Jun",
            raw_json=json.dumps({"classification": "task"}),
            created_at=base_time
        )

        db.add(sig_tomorrow)
        db.add(sig_date_pattern)
        db.add(sig_task_inherit)
        db.add(sig_named_date)
        db.commit()

        # Fetch IDs
        tomorrow_id = sig_tomorrow.id
        date_pattern_id = sig_date_pattern.id
        task_inherit_id = sig_task_inherit.id
        named_date_id = sig_named_date.id

        # 3. Classify first (so they are marked as TODO category)
        logger.info("Classifying mock signals...")
        classified_count = SignalProcessor.process_all_signals()
        assert classified_count >= 4

        # Verify they are classified as TODO
        c_tomorrow = db.query(SignalClassification).get(tomorrow_id)
        c_date_pattern = db.query(SignalClassification).get(date_pattern_id)
        c_task_inherit = db.query(SignalClassification).get(task_inherit_id)
        c_named_date = db.query(SignalClassification).get(named_date_id)
        
        # Case 3 might be classified as INSURANCE or FINANCIAL or FYI/TODO depending on summary.
        # "Renew car insurance policy" contains "insurance" -> classified as INSURANCE!
        # Ah! If sig_task_inherit is classified as INSURANCE, we want it to be classified as TODO.
        # Let's adjust its summary/category to force it as TODO:
        # e.g., "Complete task: Renew car insurance policy"
        # Wait, let's see. If the classification category is not TODO, it won't be processed.
        # Let's verify and force their classification categories in test or adjust mock signals.
        # Let's check how sig_task_inherit is classified:
        # Summary: "[TEST_TODO_EXT] Renew car insurance policy" has "insurance" -> classified as INSURANCE.
        # Let's change the summary of sig_task_inherit to "[TEST_TODO_EXT] Bring grocery items" so it classifies as TODO.
        # Let's do that! Let's update the summaries to be clearly TODO:
        # Sig 1: "Bring a Father's Day greeting card tomorrow"
        # Sig 2: "Submit science project homework by 28-06-2026"
        # Sig 3: "Renew parking pass by 06-Jul-2026"
        # Sig 4: "Book flight tickets by 28 Jun"
        # Let's modify the mocks below:
        
        # Let's delete and re-add them with correct summaries
        db.query(Signal).filter(Signal.id.in_([tomorrow_id, date_pattern_id, task_inherit_id, named_date_id])).delete()
        db.query(SignalClassification).delete()
        db.commit()

        sig_tomorrow = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",
            summary="[TEST_TODO_EXT] Bring a Father's Day greeting card tomorrow",
            raw_json=json.dumps({"classification": "task"}),
            created_at=base_time
        )
        sig_date_pattern = Signal(
            source="whatsapp",
            signal_type="school_update",
            category="education",
            importance="high",
            summary="[TEST_TODO_EXT] Submit science project homework by 28-06-2026",
            raw_json=json.dumps({"classification": "task"}),
            created_at=base_time
        )
        sig_task_inherit = Signal(
            source="sms",
            signal_type="important",
            category="general",
            importance="medium",
            summary="[TEST_TODO_EXT] Pay the electricity bill of Rs 1500",
            raw_json=json.dumps({"due_date": "2026-07-06", "classification": "task"}),
            created_at=base_time
        )
        sig_named_date = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",
            summary="[TEST_TODO_EXT] Book flight tickets by 28 Jun",
            raw_json=json.dumps({"classification": "task"}),
            created_at=base_time
        )

        db.add(sig_tomorrow)
        db.add(sig_date_pattern)
        db.add(sig_task_inherit)
        db.add(sig_named_date)
        db.commit()

        tomorrow_id = sig_tomorrow.id
        date_pattern_id = sig_date_pattern.id
        task_inherit_id = sig_task_inherit.id
        named_date_id = sig_named_date.id

        # Classify again
        logger.info("Classifying mock signals...")
        SignalProcessor.process_all_signals()

        c_tomorrow = db.query(SignalClassification).get(tomorrow_id)
        c_date_pattern = db.query(SignalClassification).get(date_pattern_id)
        c_task_inherit = db.query(SignalClassification).get(task_inherit_id)
        c_named_date = db.query(SignalClassification).get(named_date_id)

        assert c_tomorrow.category == "TODO", f"Expected TODO, got {c_tomorrow.category}"
        assert c_date_pattern.category == "TODO", f"Expected TODO, got {c_date_pattern.category}"
        assert c_task_inherit.category == "TODO", f"Expected TODO, got {c_task_inherit.category}"
        assert c_named_date.category == "TODO", f"Expected TODO, got {c_named_date.category}"

        # 4. Extract TODOs
        logger.info("Running extract_todos()...")
        extracted_count = SignalProcessor.extract_todos()
        assert extracted_count == 4, f"Expected 4 extracted TODOs, got {extracted_count}"

        # 5. Verify database records
        db.expire_all()

        todo_tomorrow = db.query(Todo).filter(Todo.source_signal_id == tomorrow_id).first()
        assert todo_tomorrow is not None
        assert todo_tomorrow.title == sig_tomorrow.summary
        assert todo_tomorrow.priority == "high"
        # base_dt + 1 day = 2026-06-22
        assert todo_tomorrow.due_date == "2026-06-22", f"Expected 2026-06-22, got {todo_tomorrow.due_date}"

        todo_date_pattern = db.query(Todo).filter(Todo.source_signal_id == date_pattern_id).first()
        assert todo_date_pattern is not None
        assert todo_date_pattern.due_date == "2026-06-28", f"Expected 2026-06-28, got {todo_date_pattern.due_date}"

        todo_task_inherit = db.query(Todo).filter(Todo.source_signal_id == task_inherit_id).first()
        assert todo_task_inherit is not None
        assert todo_task_inherit.due_date == "2026-07-06", f"Expected 2026-07-06, got {todo_task_inherit.due_date}"

        todo_named_date = db.query(Todo).filter(Todo.source_signal_id == named_date_id).first()
        assert todo_named_date is not None
        assert todo_named_date.due_date == "2026-06-28", f"Expected 2026-06-28, got {todo_named_date.due_date}"

        # 6. Verify duplicate prevention (running again should result in 0 new extractions)
        logger.info("Re-running extract_todos() to verify duplicate prevention...")
        second_run_count = SignalProcessor.extract_todos()
        assert second_run_count == 0, f"Expected 0 new extractions on second run, got {second_run_count}"

        logger.success("ALL TODO EXTRACTOR INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"Todo extractor integration tests failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_todo_extractor_tests()
