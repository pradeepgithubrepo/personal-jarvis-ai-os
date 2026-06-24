# tests/test_signal_qualification_v2.py

import sys
import os
import datetime
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.mobile_signal import MobileSignal
from storage.models.qualified_signal import QualifiedSignal
from services.signal_qualification_agent import SignalQualificationAgent


def run_v2_qualification_tests():
    logger.info("Initializing database for qualification v2 tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clear old qualified logs & mobile signals
        db.query(QualifiedSignal).delete()
        db.query(MobileSignal).filter(MobileSignal.device_id == "test_qualify_v2").delete()
        db.commit()

        # Mock Supabase Repo method to avoid making network requests
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.create_qualified_signal.return_value = True

        with patch("services.signal_qualification_agent.SupabaseRepo", mock_supabase_repo):
            
            logger.info("Inserting mock mobile signals representing various types...")
            now = datetime.datetime.utcnow()

            # Test Set of Signals:
            
            # 1. School message (Qualified after boost, Review before)
            sig_school = MobileSignal(
                device_id="test_qualify_v2",
                source="whatsapp",
                sender="Class Teacher",
                message="School Circular: Parent teacher meeting schedule details attached.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 2. Spouse message (Qualified after boost, Review before)
            sig_spouse = MobileSignal(
                device_id="test_qualify_v2",
                source="whatsapp",
                sender="Shobana",
                message="Please pick up Charan from school today.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 3. Normal Badminton Group Message (Remains REVIEW)
            sig_badminton = MobileSignal(
                device_id="test_qualify_v2",
                source="whatsapp",
                sender="Badminton Group",
                message="Badminton session at 6 AM tomorrow.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 4. Bank promo that contains financial keywords (Preserved to REVIEW instead of REJECTED)
            sig_bank_promo = MobileSignal(
                device_id="test_qualify_v2",
                source="sms",
                sender="SBI-PR",
                message="Congratulations! Your credit card bill payment due of Rs 2500 has cashback offers.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 5. Non-txn promotional spam (Unconditionally Rejected)
            sig_promo = MobileSignal(
                device_id="test_qualify_v2",
                source="sms",
                sender="SBILoan",
                message="Pre-approved personal loan offer. Apply today.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            test_signals = [sig_school, sig_spouse, sig_badminton, sig_bank_promo, sig_promo]
            for s in test_signals:
                db.add(s)
            db.commit()

            # PART 1: Simulate v1 (No business context configurations loaded)
            logger.info("--- PART 1: Qualifying signals WITHOUT business context (v1 baseline) ---")
            # Force empty configurations
            SignalQualificationAgent._family_context = {}
            SignalQualificationAgent._high_value_domains = {}
            SignalQualificationAgent._qualification_rules = {}

            # Qualify each signal and capture outputs
            v1_results = []
            for s in test_signals:
                res = SignalQualificationAgent.qualify_signal(
                    db_session=db,
                    signal_id=str(s.id),
                    source=s.source,
                    sender=s.sender,
                    message=s.message,
                    raw_ts_str=s.mobile_timestamp
                )
                v1_results.append((s, res.qualification_status, res.qualification_score))

            # Clean up qualified signals table for Part 2 run
            db.query(QualifiedSignal).delete()
            db.commit()

            # PART 2: Qualify WITH business context configurations (v2)
            logger.info("--- PART 2: Qualifying signals WITH business context (v2) ---")
            # Reload configurations from config files
            SignalQualificationAgent.load_configs()

            v2_results = []
            for s in test_signals:
                res = SignalQualificationAgent.qualify_signal(
                    db_session=db,
                    signal_id=str(s.id),
                    source=s.source,
                    sender=s.sender,
                    message=s.message,
                    raw_ts_str=s.mobile_timestamp
                )
                v2_results.append((s, res.qualification_status, res.qualification_score))

            # Collate metrics
            v1_qualified = sum(1 for r in v1_results if r[1] == "QUALIFIED")
            v1_review = sum(1 for r in v1_results if r[1] == "REVIEW")
            v1_rejected = sum(1 for r in v1_results if r[1] == "REJECTED")

            v2_qualified = sum(1 for r in v2_results if r[1] == "QUALIFIED")
            v2_review = sum(1 for r in v2_results if r[1] == "REVIEW")
            v2_rejected = sum(1 for r in v2_results if r[1] == "REJECTED")

            # Output the comparative report
            print("\n" + "="*60)
            print("     COMPARATIVE VALIDATION REPORT: Module 2A.2     ")
            print("="*60)
            print(f"Metrics:                 | Before (v1) | After (v2)")
            print("-"*60)
            print(f"Total Qualified Signals  | {v1_qualified}           | {v2_qualified}")
            print(f"Total Review Required    | {v1_review}           | {v2_review}")
            print(f"Total Rejected (Noise)   | {v1_rejected}           | {v2_rejected}")
            print("-"*60)
            
            print("Example Signals Upgraded To QUALIFIED:")
            # Find signals that went from REVIEW -> QUALIFIED
            for idx in range(len(test_signals)):
                orig_status = v1_results[idx][1]
                new_status = v2_results[idx][1]
                sig = test_signals[idx]
                if orig_status == "REVIEW" and new_status == "QUALIFIED":
                    print(f"  * Upgraded: [{sig.source}] {sig.sender}: '{sig.message}'")
                    print(f"    (Score: {v1_results[idx][2]} -> {v2_results[idx][2]})")

            print("\nExample Signals Remaining REVIEW:")
            # Find signals that remained REVIEW in both
            for idx in range(len(test_signals)):
                orig_status = v1_results[idx][1]
                new_status = v2_results[idx][1]
                sig = test_signals[idx]
                if orig_status == "REVIEW" and new_status == "REVIEW":
                    print(f"  * Retained: [{sig.source}] {sig.sender}: '{sig.message}'")
                    print(f"    (Score: {v1_results[idx][2]} -> {v2_results[idx][2]})")

            print("\nExample Signals Preserved to REVIEW (Not Discarded):")
            # Find signals that went from REJECTED -> REVIEW
            for idx in range(len(test_signals)):
                orig_status = v1_results[idx][1]
                new_status = v2_results[idx][1]
                sig = test_signals[idx]
                if orig_status == "REJECTED" and new_status == "REVIEW":
                    print(f"  * Preserved: [{sig.source}] {sig.sender}: '{sig.message}'")
                    print(f"    (Score: {v1_results[idx][2]} -> {v2_results[idx][2]})")
            print("="*60 + "\n")

            # Verification Assertions
            # 1. School circular should be upgraded to QUALIFIED
            assert v2_results[0][1] == "QUALIFIED", "Expected school circular to be qualified"
            # 2. Spouse request should be upgraded to QUALIFIED
            assert v2_results[1][1] == "QUALIFIED", "Expected spouse request to be qualified"
            # 3. Badminton should remain REVIEW
            assert v2_results[2][1] == "REVIEW", "Expected badminton group chat to remain in review"
            # 4. Financial promo containing bill payment keywords should be preserved as REVIEW
            assert v2_results[3][1] == "REVIEW", "Expected financial payment notification to be preserved as review"
            
            logger.success("Signal Qualification Context Layer verified successfully!")

    finally:
        # Clean up
        db.query(QualifiedSignal).delete()
        db.query(MobileSignal).filter(MobileSignal.device_id == "test_qualify_v2").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_v2_qualification_tests()
