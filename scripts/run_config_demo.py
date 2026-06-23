# scripts/run_config_demo.py

import os
import sys
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


def run_demo():
    print("\n" + "="*80)
    print("                JARVIS CONFIG-DRIVEN CLASSIFICATION DEMO")
    print("="*80)

    logger.info("Initializing database...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clean up any old demo records
        db.query(FinancialEvent).filter(FinancialEvent.title.like("%[DEMO_RULE]%")).delete(synchronize_session=False)
        db.query(CategoryCorrection).filter(CategoryCorrection.merchant == "demo_zepto").delete(synchronize_session=False)
        db.query(SignalClassification).delete()
        db.query(Signal).filter(Signal.summary.like("%[DEMO_RULE]%")).delete(synchronize_session=False)
        db.commit()

        # Reset overrides config file for the demo
        overrides_path = LearningEngine.OVERRIDES_FILE
        try:
            with open(overrides_path, "w") as f:
                json.dump({"overrides": {}}, f, indent=2)
            RulesEngine.reload()
            logger.info("Reset user_overrides.json successfully.")
        except Exception as e:
            logger.error(f"Failed to reset overrides config file: {e}")

        # ----------------------------------------------------------------------
        # 1. Config Ignore Rules Demo
        # ----------------------------------------------------------------------
        print("\n" + "-"*80)
        print(" 1. CONFIG-DRIVEN IGNORE TOPICS DEMO")
        print("-"*80)
        print("Inserting a signal containing 'badminton' (defined in ignore_topics)...")
        sig_ignore = Signal(
            source="whatsapp",
            signal_type="personal_chat",
            category="personal",
            importance="low",
            summary="[DEMO_RULE] Let's play badminton at 5pm",
            raw_json=json.dumps({"classification": "chat"}),
        )
        db.add(sig_ignore)
        db.commit()

        # Process classification
        SignalProcessor.process_all_signals()
        
        class_ignore = db.query(SignalClassification).filter(
            SignalClassification.signal_id == sig_ignore.id
        ).first()
        print(f"Signal: '{sig_ignore.summary}'")
        print(f"Resolved Classification Category: {class_ignore.category} (Expected: IGNORE)")

        # ----------------------------------------------------------------------
        # 2. Spend Categories Default Matching Demo
        # ----------------------------------------------------------------------
        print("\n" + "-"*80)
        print(" 2. SPEND CATEGORY CONFIGURATION MATCHING DEMO")
        print("-"*80)
        print("Inserting a financial transaction with merchant 'zepto'...")
        print("(Note: 'zepto' maps to default category 'GROCERY' in jarvis_rules.json)")
        
        sig_grocery = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[DEMO_RULE] Spent Rs 300 at demo_zepto",
            raw_json=json.dumps({"amount": "300.00", "paid_to": "demo_zepto"}),
        )
        db.add(sig_grocery)
        db.commit()

        # Run process & extract
        db.query(SignalClassification).delete()
        db.commit()
        SignalProcessor.process_all_signals()
        SignalProcessor.extract_financial_events()

        evt_grocery = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_grocery.id).first()
        print(f"Transaction: '{evt_grocery.title}'")
        print(f"Merchant resolved: '{evt_grocery.paid_to}'")
        print(f"Initial Spend Category resolved: {evt_grocery.category} (Expected: GROCERY)")

        # ----------------------------------------------------------------------
        # 3. Learning Overrides Sequence Demo
        # ----------------------------------------------------------------------
        print("\n" + "-"*80)
        print(" 3. LEARNING OVERRIDES & AUTOMATIC PROMOTION DEMO")
        print("-"*80)
        print("We will simulate correcting category to 'VEGETABLES' 3 times for merchant 'demo_zepto'...")
        
        # We need three separate events to trigger distinct corrections
        sig_z1 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[DEMO_RULE] Spent Rs 150 on demo_zepto purchase 1",
            raw_json=json.dumps({"amount": "150.00", "paid_to": "demo_zepto"}),
        )
        sig_z2 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[DEMO_RULE] Spent Rs 200 on demo_zepto purchase 2",
            raw_json=json.dumps({"amount": "200.00", "paid_to": "demo_zepto"}),
        )
        sig_z3 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[DEMO_RULE] Spent Rs 250 on demo_zepto purchase 3",
            raw_json=json.dumps({"amount": "250.00", "paid_to": "demo_zepto"}),
        )
        db.add(sig_z1)
        db.add(sig_z2)
        db.add(sig_z3)
        db.commit()

        # Extract events
        db.query(SignalClassification).delete()
        db.query(FinancialEvent).filter(FinancialEvent.title.like("%demo_zepto%")).delete(synchronize_session=False)
        db.commit()
        SignalProcessor.process_all_signals()
        SignalProcessor.extract_financial_events()

        evt_z1 = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_z1.id).first()
        evt_z2 = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_z2.id).first()
        evt_z3 = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_z3.id).first()

        # Correction 1
        print("\nApplying manual correction 1...")
        LearningEngine.correct_category(db, evt_z1.id, "VEGETABLES")
        corr1 = db.query(CategoryCorrection).filter(CategoryCorrection.merchant == "demo_zepto").first()
        print(f"Correction count in DB: {corr1.correction_count if corr1 else 0}")
        
        # Correction 2
        print("Applying manual correction 2...")
        LearningEngine.correct_category(db, evt_z2.id, "VEGETABLES")
        corr2 = db.query(CategoryCorrection).filter(CategoryCorrection.merchant == "demo_zepto").first()
        print(f"Correction count in DB: {corr2.correction_count if corr2 else 0}")

        # Checking override config on disk (should be empty still)
        with open(overrides_path, "r") as f:
            disk_overrides = json.load(f).get("overrides", {})
        print(f"Overrides on disk before threshold: {disk_overrides}")

        # Correction 3
        print("Applying manual correction 3 (Triggering Threshold!)...")
        LearningEngine.correct_category(db, evt_z3.id, "VEGETABLES")
        corr3 = db.query(CategoryCorrection).filter(CategoryCorrection.merchant == "demo_zepto").first()
        print(f"Correction count in DB: {corr3.correction_count if corr3 else 0}")

        # Checking override config on disk (should now contain "demo_zepto": "VEGETABLES")
        with open(overrides_path, "r") as f:
            disk_overrides_after = json.load(f).get("overrides", {})
        print(f"Overrides on disk AFTER threshold: {disk_overrides_after}")

        # ----------------------------------------------------------------------
        # 4. Verification of Automatic Reload and Overrides
        # ----------------------------------------------------------------------
        print("\n" + "-"*80)
        print(" 4. CONFIRMING CODE-FREE DYNAMIC CLASSIFICATION IN ACTION")
        print("-"*80)
        print("Inserting a brand new 'demo_zepto' signal...")
        print("Since RulesEngine was reloaded, it should map to VEGETABLES automatically!")
        
        sig_zepto_new = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[DEMO_RULE] Spent Rs 400 at demo_zepto for dinner ingredients",
            raw_json=json.dumps({"amount": "400.00", "paid_to": "demo_zepto"}),
        )
        db.add(sig_zepto_new)
        db.commit()

        # Process new signal
        SignalProcessor.process_all_signals()
        SignalProcessor.extract_financial_events()

        evt_zepto_new = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == sig_zepto_new.id).first()
        print(f"New Transaction: '{evt_zepto_new.title}'")
        print(f"Resolved Category: {evt_zepto_new.category} (Expected: VEGETABLES)")

        print("\n" + "="*80)
        print("                  JARVIS CONFIG DEMO COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")

    finally:
        # Clean up demo files and database records to keep codebase clean
        try:
            with open(overrides_path, "w") as f:
                json.dump({"overrides": {}}, f, indent=2)
            RulesEngine.reload()
        except Exception:
            pass
        db.query(FinancialEvent).filter(FinancialEvent.title.like("%[DEMO_RULE]%")).delete(synchronize_session=False)
        db.query(CategoryCorrection).filter(CategoryCorrection.merchant == "demo_zepto").delete(synchronize_session=False)
        db.query(SignalClassification).delete()
        db.query(Signal).filter(Signal.summary.like("%[DEMO_RULE]%")).delete(synchronize_session=False)
        db.commit()
        db.close()


if __name__ == "__main__":
    run_demo()
