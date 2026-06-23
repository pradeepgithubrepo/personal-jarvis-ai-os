# tests/test_rules_config.py

import sys
import os
import json
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from storage.models.financial_event import FinancialEvent
from storage.models.category_correction import CategoryCorrection
from services.signal_processor import SignalProcessor
from services.rules_engine import RulesEngine
from services.learning_engine import LearningEngine


def run_rules_config_tests():
    logger.info("Initializing database for configuration rules tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # 1. Clean up old test data
        logger.info("Cleaning up old test data...")
        db.query(FinancialEvent).delete()
        db.query(CategoryCorrection).delete()
        db.query(SignalClassification).delete()
        db.query(Signal).filter(Signal.summary.like("%[TEST_RULE]%")).delete(synchronize_session=False)
        db.commit()

        # Reset overrides config file to clear previous test overrides
        overrides_path = LearningEngine.OVERRIDES_FILE
        try:
            with open(overrides_path, "w") as f:
                json.dump({"overrides": {}}, f, indent=2)
            logger.info("Reset user_overrides.json file successfully.")
            RulesEngine.reload()
        except Exception as e:
            logger.error(f"Failed to reset overrides config file: {e}")

        # 2. Test Ignore Topics Config Rules
        logger.info("Test Case 1: Verifying config-driven ignore topics...")
        sig_badminton = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="low",
            summary="[TEST_RULE] Hey are you ready for badminton racket practice tomorrow?",
            raw_json=json.dumps({"classification": "chat"}),
        )
        db.add(sig_badminton)
        db.commit()

        # Classify signals
        SignalProcessor.process_all_signals()
        
        # Check classification
        class_badminton = db.query(SignalClassification).filter(
            SignalClassification.signal_id == sig_badminton.id
        ).first()
        assert class_badminton is not None
        assert class_badminton.category == "IGNORE", f"Expected IGNORE, got {class_badminton.category}"
        logger.success("Test Case 1: Ignore Topics verified successfully.")

        # Test Case 1b: Badminton exceptions should NOT be ignored and priority set to low
        logger.info("Test Case 1b: Verifying badminton ignore exceptions...")
        sig_badminton_exc = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="high",  # Start with high importance to test override
            summary="[TEST_RULE] Sorry guys, I am not coming for badminton tomorrow",
            raw_json=json.dumps({"classification": "chat"}),
        )
        db.add(sig_badminton_exc)
        db.commit()

        # Reset classification table and run again to process the new signal
        db.query(SignalClassification).delete()
        db.commit()
        SignalProcessor.process_all_signals()

        class_badminton_exc = db.query(SignalClassification).filter(
            SignalClassification.signal_id == sig_badminton_exc.id
        ).first()
        assert class_badminton_exc is not None
        assert class_badminton_exc.category != "IGNORE", f"Expected not IGNORE, got {class_badminton_exc.category}"
        
        # Reload signal to verify importance override
        db.refresh(sig_badminton_exc)
        assert sig_badminton_exc.importance == "low", f"Expected importance low, got {sig_badminton_exc.importance}"
        logger.success("Test Case 1b: Badminton Ignore Exceptions verified successfully.")

        # 3. Test Financial Exclusions Config Rules
        logger.info("Test Case 2: Verifying financial exclusions ignore rules...")
        sig_cashback = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Cashback credited! You received reward points Rs.50",
            raw_json=json.dumps({"amount": "50.00", "transaction_type": "credit"}),
        )
        db.add(sig_cashback)
        db.commit()

        # Reset classification table and run again to process the new signal
        db.query(SignalClassification).delete()
        db.commit()
        SignalProcessor.process_all_signals()

        class_cashback = db.query(SignalClassification).filter(
            SignalClassification.signal_id == sig_cashback.id
        ).first()
        assert class_cashback is not None
        assert class_cashback.category == "IGNORE", f"Expected IGNORE, got {class_cashback.category}"
        logger.success("Test Case 2: Financial Exclusions verified successfully.")

        # 4. Test Categorization Lookup Hierarchy (Merchant -> UPI -> Custom -> OTHER)
        logger.info("Test Case 3: Verifying spend categorization hierarchy...")
        
        # 4.1 Merchant Default Category
        sig_amazon = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Rs 450.00 spent on Amazon Pay",
            raw_json=json.dumps({"amount": "450.00", "merchant": "Amazon"}),
        )
        # 4.2 UPI VPA Pattern
        sig_upi_fam = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] UPI payment of Rs.2000 to shobanakumari@okaxis",
            raw_json=json.dumps({"amount": "2000.00", "paid_to": "shobanakumari@okaxis"}),
        )
        # 4.3 Custom Keyword Category
        sig_custom_fish = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Paid Rs 350 to meen shop",
            raw_json=json.dumps({"amount": "350.00", "paid_to": "meen shop"}),
        )
        # 4.4 Fallback Category
        sig_fallback = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Paid Rs 500 at unrelated store",
            raw_json=json.dumps({"amount": "500.00", "paid_to": "unrelated store"}),
        )

        db.add(sig_amazon)
        db.add(sig_upi_fam)
        db.add(sig_custom_fish)
        db.add(sig_fallback)
        db.commit()

        # Run process and extract
        db.query(SignalClassification).delete()
        db.commit()
        SignalProcessor.process_all_signals()
        SignalProcessor.extract_financial_events()

        # Assert Categories
        evt_amazon = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_amazon.id).first()
        assert evt_amazon is not None
        assert evt_amazon.category == "SHOPPING", f"Expected SHOPPING, got {evt_amazon.category}"

        evt_upi = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_upi_fam.id).first()
        assert evt_upi is not None
        assert evt_upi.category == "FAMILY", f"Expected FAMILY, got {evt_upi.category}"

        evt_fish = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_custom_fish.id).first()
        assert evt_fish is not None
        assert evt_fish.category == "FISH", f"Expected FISH, got {evt_fish.category}"

        evt_fallback = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_fallback.id).first()
        assert evt_fallback is not None
        assert evt_fallback.category == "OTHER", f"Expected OTHER, got {evt_fallback.category}"
        logger.success("Test Case 3: Categorization Hierarchy verified successfully.")

        # 5. Test Learning Engine & Overrides threshold
        logger.info("Test Case 4: Verifying manual corrections & learning engine overrides...")
        
        # Step 5.1: Create mock Zepto transactions
        # Zepto initially maps to GROCERY in jarvis_rules.json
        sig_zepto1 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Rs 250 spent on Zepto delivery 1",
            raw_json=json.dumps({"amount": "250.00", "paid_to": "zepto"}),
        )
        sig_zepto2 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Rs 300 spent on Zepto delivery 2",
            raw_json=json.dumps({"amount": "300.00", "paid_to": "zepto"}),
        )
        sig_zepto3 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Rs 350 spent on Zepto delivery 3",
            raw_json=json.dumps({"amount": "350.00", "paid_to": "zepto"}),
        )
        db.add(sig_zepto1)
        db.add(sig_zepto2)
        db.add(sig_zepto3)
        db.commit()

        # Re-run processor & extractor
        db.query(SignalClassification).delete()
        db.query(FinancialEvent).delete()
        db.commit()
        SignalProcessor.process_all_signals()
        SignalProcessor.extract_financial_events()

        evt_zepto1 = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_zepto1.id).first()
        evt_zepto2 = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_zepto2.id).first()
        evt_zepto3 = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_zepto3.id).first()
        
        assert evt_zepto1 is not None and evt_zepto2 is not None and evt_zepto3 is not None
        assert evt_zepto1.category == "GROCERY", f"Expected default GROCERY, got {evt_zepto1.category}"

        # Step 5.2: Simulate 3 category corrections (Zepto -> VEGETABLES)
        # Correction 1
        success1 = LearningEngine.correct_category(db, evt_zepto1.id, "VEGETABLES")
        assert success1 is True
        
        # Check overrides on disk - shouldn't have promoted yet (count = 1)
        with open(overrides_path, "r") as f:
            overrides = json.load(f).get("overrides", {})
        assert "zepto" not in overrides

        # Correction 2
        success2 = LearningEngine.correct_category(db, evt_zepto2.id, "VEGETABLES")
        assert success2 is True
        with open(overrides_path, "r") as f:
            overrides = json.load(f).get("overrides", {})
        assert "zepto" not in overrides

        # Correction 3 - triggers promotion
        success3 = LearningEngine.correct_category(db, evt_zepto3.id, "VEGETABLES")
        assert success3 is True

        # Check overrides on disk - should be promoted now (count = 3)
        with open(overrides_path, "r") as f:
            overrides = json.load(f).get("overrides", {})
        assert overrides.get("zepto") == "VEGETABLES"

        # Step 5.3: Verify that a new Zepto signal automatically maps to VEGETABLES (due to override reload)
        sig_zepto_new = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_RULE] Rs 400 spent on Zepto app store",
            raw_json=json.dumps({"amount": "400.00", "paid_to": "zepto"}),
        )
        db.add(sig_zepto_new)
        db.commit()

        # Re-run processor & extractor
        SignalProcessor.process_all_signals()
        SignalProcessor.extract_financial_events()

        evt_zepto_new = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_zepto_new.id).first()
        assert evt_zepto_new is not None
        assert evt_zepto_new.category == "VEGETABLES", f"Expected VEGETABLES override, got {evt_zepto_new.category}"
        logger.success("Test Case 4: Manual corrections & learning overrides verified successfully.")

        logger.success("ALL CONFIG DRIVEN RULES ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"Config rules engine tests failed: {e}")
        raise e
    finally:
        # Cleanup overrides file
        try:
            with open(overrides_path, "w") as f:
                json.dump({"overrides": {}}, f, indent=2)
            RulesEngine.reload()
        except Exception:
            pass
        # Clean up database
        db.query(FinancialEvent).delete()
        db.query(CategoryCorrection).delete()
        db.query(SignalClassification).delete()
        db.query(Signal).filter(Signal.summary.like("%[TEST_RULE]%")).delete(synchronize_session=False)
        db.commit()
        db.close()


if __name__ == "__main__":
    run_rules_config_tests()
