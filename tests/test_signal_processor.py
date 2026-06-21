# tests/test_signal_processor.py

import sys
import os
import json
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from storage.models.task import Task
from services.signal_processor import SignalProcessor


def run_processor_tests():
    logger.info("Initializing database schema...")
    initialize_database()

    db = SessionLocal()
    try:
        # 1. Clean up existing test data
        logger.info("Cleaning up old test signals...")
        db.query(SignalClassification).delete()
        db.query(Signal).filter(Signal.summary.like("%[TEST_SIG_PROC]%")).delete()
        db.query(Task).filter(Task.title.like("%[TEST_SIG_PROC]%")).delete()
        db.commit()

        # 2. Add mock signals for classification
        logger.info("Inserting mock signals...")

        # Case 1: OTP -> IGNORE
        sig_ignore = Signal(
            source="sms",
            signal_type="otp",
            category="security",
            importance="ignore",
            summary="[TEST_SIG_PROC] OTP: Your verification code is 445522. Do not share.",
            raw_json=json.dumps({"otp_code": "445522", "service": "HDFC"})
        )

        # Case 2: Insurance Renewal -> INSURANCE
        sig_insurance = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_SIG_PROC] Dear customer, your HDFC Ergo car insurance policy renewal premium is due on 28-Jun-2026. Pay Rs. 6500.",
            raw_json=json.dumps({"amount": "6500.00", "currency": "INR"})
        )

        # Case 3: Credit alert -> FINANCIAL
        sig_financial = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_SIG_PROC] Account XX3221 credited with Rs 50,000.00 via NEFT. Avl Bal Rs 52,000.00.",
            raw_json=json.dumps({"amount": "50000.00", "currency": "INR", "transaction_type": "credit"})
        )

        # Case 4: Actionable WhatsApp -> TODO
        sig_todo = Signal(
            source="whatsapp",
            signal_type="school_update",
            category="education",
            importance="high",
            summary="[TEST_SIG_PROC] Class teacher: Please submit the science project model by Wednesday.",
            raw_json=json.dumps({"classification": "task", "action_items": ["submit science project"]})
        )
        
        # Insert a dummy task to simulate associated task in DB
        task_todo = Task(
            title="[TEST_SIG_PROC] Class teacher: Please submit the science project model by Wednesday.",
            category="education",
            priority="high",
            source="whatsapp"
        )
        db.add(task_todo)

        # Case 5: School FYI WhatsApp -> FYI
        sig_fyi_school = Signal(
            source="whatsapp",
            signal_type="school_update",
            category="education",
            importance="high",
            summary="[TEST_SIG_PROC] School circular: School will remain closed tomorrow due to rain update.",
            raw_json=json.dumps({"classification": "FYI", "action_items": []})
        )

        # Case 6: Delivery -> FYI
        sig_fyi_delivery = Signal(
            source="sms",
            signal_type="delivery_update",
            category="shopping",
            importance="low",
            summary="[TEST_SIG_PROC] Your package from Amazon is out for delivery today.",
            raw_json=json.dumps({"merchant": "Amazon", "order_status": "Out for Delivery"})
        )

        # Case 7: General fallback -> FYI with 0.8 confidence
        sig_fallback = Signal(
            source="sms",
            signal_type="general",
            category="general",
            importance="low",
            summary="[TEST_SIG_PROC] Random text about system storage space.",
            raw_json=None
        )

        db.add(sig_ignore)
        db.add(sig_insurance)
        db.add(sig_financial)
        db.add(sig_todo)
        db.add(sig_fyi_school)
        db.add(sig_fyi_delivery)
        db.add(sig_fallback)
        db.commit()

        # Retrieve IDs
        ignore_id = sig_ignore.id
        insurance_id = sig_insurance.id
        financial_id = sig_financial.id
        todo_id = sig_todo.id
        fyi_school_id = sig_fyi_school.id
        fyi_delivery_id = sig_fyi_delivery.id
        fallback_id = sig_fallback.id

        logger.info("Mock signals inserted. Running Signal Classification Processor...")
        processed_count = SignalProcessor.process_all_signals()
        assert processed_count >= 7, f"Expected at least 7 processed signals, got {processed_count}"

        # 3. Assert classifications
        db.expire_all()

        c_ignore = db.query(SignalClassification).get(ignore_id)
        assert c_ignore is not None, "Classification for IGNORE signal missing!"
        assert c_ignore.category == "IGNORE", f"Expected IGNORE, got {c_ignore.category}"
        assert c_ignore.confidence == 1.0, f"Expected confidence 1.0, got {c_ignore.confidence}"

        c_insurance = db.query(SignalClassification).get(insurance_id)
        assert c_insurance is not None, "Classification for INSURANCE signal missing!"
        assert c_insurance.category == "INSURANCE", f"Expected INSURANCE, got {c_insurance.category}"
        assert c_insurance.confidence == 1.0, f"Expected confidence 1.0, got {c_insurance.confidence}"

        c_financial = db.query(SignalClassification).get(financial_id)
        assert c_financial is not None, "Classification for FINANCIAL signal missing!"
        assert c_financial.category == "FINANCIAL", f"Expected FINANCIAL, got {c_financial.category}"
        assert c_financial.confidence == 1.0, f"Expected confidence 1.0, got {c_financial.confidence}"

        c_todo = db.query(SignalClassification).get(todo_id)
        assert c_todo is not None, "Classification for TODO signal missing!"
        assert c_todo.category == "TODO", f"Expected TODO, got {c_todo.category}"
        assert c_todo.confidence == 1.0, f"Expected confidence 1.0, got {c_todo.confidence}"

        c_fyi_school = db.query(SignalClassification).get(fyi_school_id)
        assert c_fyi_school is not None, "Classification for School FYI signal missing!"
        assert c_fyi_school.category == "FYI", f"Expected FYI, got {c_fyi_school.category}"
        assert c_fyi_school.confidence == 1.0, f"Expected confidence 1.0, got {c_fyi_school.confidence}"

        c_fyi_delivery = db.query(SignalClassification).get(fyi_delivery_id)
        assert c_fyi_delivery is not None, "Classification for Delivery FYI signal missing!"
        assert c_fyi_delivery.category == "FYI", f"Expected FYI, got {c_fyi_delivery.category}"
        assert c_fyi_delivery.confidence == 1.0, f"Expected confidence 1.0, got {c_fyi_delivery.confidence}"

        c_fallback = db.query(SignalClassification).get(fallback_id)
        assert c_fallback is not None, "Classification for Fallback signal missing!"
        assert c_fallback.category == "FYI", f"Expected FYI, got {c_fallback.category}"
        assert c_fallback.confidence == 0.8, f"Expected confidence 0.8, got {c_fallback.confidence}"

        logger.success("ALL SIGNAL PROCESSOR INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"SignalProcessor integration tests failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_processor_tests()
