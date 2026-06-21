# tests/test_fyi_extractor.py

import sys
import os
import json
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from storage.models.fyi_event import FyiEvent
from services.signal_processor import SignalProcessor


def run_fyi_extractor_tests():
    logger.info("Initializing database schema...")
    initialize_database()

    db = SessionLocal()
    try:
        # 1. Clean up old test data
        logger.info("Cleaning up old test data...")
        db.query(FyiEvent).delete()
        db.query(SignalClassification).delete()
        db.query(Signal).filter(
            (Signal.summary.like("%[TEST_FYI_EXT]%")) | (Signal.summary.like("%[TEST_SIG_PROC]%"))
        ).delete(synchronize_session=False)
        db.commit()

        # 2. Add mock signals
        logger.info("Inserting mock FYI signals...")
        base_time = datetime(2026, 6, 21, 12, 0, 0)

        # Case 1: Delivery alert
        sig_delivery = Signal(
            source="sms",
            signal_type="delivery_update",
            category="shopping",
            importance="low",
            summary="[TEST_FYI_EXT] Your parcel has been delivered to the reception.",
            raw_json=json.dumps({"merchant": "DHL", "order_status": "delivered"}),
            created_at=base_time
        )

        # Case 2: School FYI
        sig_school = Signal(
            source="whatsapp",
            signal_type="school_update",
            category="education",
            importance="high",
            summary="[TEST_FYI_EXT] School circular: Rain update - school remains open today.",
            raw_json=json.dumps({"classification": "FYI"}),
            created_at=base_time
        )

        # Case 3: Travel status
        sig_travel = Signal(
            source="email",
            signal_type="important",
            category="general",
            importance="high",
            summary="[TEST_FYI_EXT] Flight booking reference ABC123 confirmed.",
            raw_json=json.dumps({}),
            created_at=base_time
        )

        # Case 4: Family update
        sig_family = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",
            summary="[TEST_FYI_EXT] Wife: We are visiting kids' grandparents this evening.",
            raw_json=json.dumps({"classification": "FYI"}),
            created_at=base_time
        )

        db.add(sig_delivery)
        db.add(sig_school)
        db.add(sig_travel)
        db.add(sig_family)
        db.commit()

        delivery_id = sig_delivery.id
        school_id = sig_school.id
        travel_id = sig_travel.id
        family_id = sig_family.id

        # 3. Classify first
        logger.info("Classifying mock signals...")
        SignalProcessor.process_all_signals()

        c_delivery = db.query(SignalClassification).get(delivery_id)
        c_school = db.query(SignalClassification).get(school_id)
        c_travel = db.query(SignalClassification).get(travel_id)
        c_family = db.query(SignalClassification).get(family_id)

        assert c_delivery.category == "FYI", f"Expected FYI, got {c_delivery.category}"
        assert c_school.category == "FYI", f"Expected FYI, got {c_school.category}"
        assert c_travel.category == "FYI", f"Expected FYI, got {c_travel.category}"
        assert c_family.category == "FYI", f"Expected FYI, got {c_family.category}"

        # 4. Extract FYI events
        logger.info("Running extract_fyi_events()...")
        extracted_count = SignalProcessor.extract_fyi_events()
        assert extracted_count >= 4, f"Expected at least 4 extracted FYI events, got {extracted_count}"

        # 5. Verify database records
        db.expire_all()

        event_delivery = db.query(FyiEvent).filter(FyiEvent.source_signal_id == delivery_id).first()
        assert event_delivery is not None
        assert event_delivery.fyi_type == "delivery_notification"
        assert event_delivery.title == sig_delivery.summary

        event_school = db.query(FyiEvent).filter(FyiEvent.source_signal_id == school_id).first()
        assert event_school is not None
        assert event_school.fyi_type == "school_circular"

        event_travel = db.query(FyiEvent).filter(FyiEvent.source_signal_id == travel_id).first()
        assert event_travel is not None
        assert event_travel.fyi_type == "travel_update"

        event_family = db.query(FyiEvent).filter(FyiEvent.source_signal_id == family_id).first()
        assert event_family is not None
        assert event_family.fyi_type == "family_update"

        # 6. Verify duplicate prevention
        logger.info("Re-running extract_fyi_events() to verify duplicate prevention...")
        second_run_count = SignalProcessor.extract_fyi_events()
        assert second_run_count == 0, f"Expected 0 new extractions on second run, got {second_run_count}"

        logger.success("ALL FYI EXTRACTOR INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"FYI extractor integration tests failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_fyi_extractor_tests()
