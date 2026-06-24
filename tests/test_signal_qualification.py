# tests/test_signal_qualification.py

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


def run_qualification_tests():
    logger.info("Initializing database for qualification tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clear old qualified logs & mobile signals
        db.query(QualifiedSignal).delete()
        db.query(MobileSignal).filter(MobileSignal.device_id == "test_qualify_device").delete()
        db.commit()

        # Mock Supabase Repo method to avoid making network requests
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.create_qualified_signal.return_value = True

        with patch("services.signal_qualification_agent.SupabaseRepo", mock_supabase_repo):
            
            logger.info("Inserting mock mobile signals representing various types...")
            now = datetime.datetime.utcnow()

            # 1. OTP message (Rejected)
            sig_otp = MobileSignal(
                device_id="test_qualify_device",
                source="sms",
                sender="HDFCBK",
                message="Your HDFC Bank transaction OTP code is 998811. Do not share.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 2. Family update (Qualified)
            sig_family = MobileSignal(
                device_id="test_qualify_device",
                source="whatsapp",
                sender="Shobana",
                message="Bring the school science model when you come home.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 3. Stale SMS older than 90 days (Rejected)
            stale_time = now - datetime.timedelta(days=95)
            sig_stale = MobileSignal(
                device_id="test_qualify_device",
                source="sms",
                sender="SBI",
                message="Your monthly account statement is ready.",
                mobile_timestamp=str(int(stale_time.timestamp() * 1000)),
                processed=False
            )

            # 4. Group badminton message (Review)
            sig_group = MobileSignal(
                device_id="test_qualify_device",
                source="whatsapp",
                sender="Badminton Group",
                message="Are we playing badminton tomorrow morning?",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 5. Normal Transaction (Qualified)
            sig_txn = MobileSignal(
                device_id="test_qualify_device",
                source="sms",
                sender="HDFCBK",
                message="Spent Rs. 450.00 on Zomato via UPI.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            # 6. Duplicate transaction alert (Rejected)
            sig_dup = MobileSignal(
                device_id="test_qualify_device",
                source="sms",
                sender="HDFCBK",
                message="Spent Rs. 450.00 on Zomato via UPI.",
                mobile_timestamp=str(int(now.timestamp() * 1000)),
                processed=False
            )

            db.add(sig_otp)
            db.add(sig_family)
            db.add(sig_stale)
            db.add(sig_group)
            db.add(sig_txn)
            db.add(sig_dup)
            db.commit()

            logger.info("Running deterministic Qualification Agent on unprocessed signals...")
            stats = SignalQualificationAgent.qualify_all_unprocessed_signals()

            # Verify metrics
            assert stats["processed"] == 6, f"Expected 6 processed, got {stats['processed']}"
            assert stats["qualified"] == 2, f"Expected 2 qualified (family + transaction), got {stats['qualified']}"
            assert stats["review"] == 1, f"Expected 1 review (group), got {stats['review']}"
            assert stats["rejected"] == 3, f"Expected 3 rejected (otp, stale, dup), got {stats['rejected']}"
            
            reasons = stats["reasons"]
            assert reasons.get("OTP") == 1, "Expected 1 OTP rejection"
            assert reasons.get("STALE_SIGNAL") == 1, "Expected 1 Stale rejection"
            assert reasons.get("DUPLICATE_SIGNAL") == 1, "Expected 1 Duplicate rejection"

            logger.success("Signal qualification statistics successfully verified!")

            # Verify SQLite persistence
            db.expire_all()
            q_signals = db.query(QualifiedSignal).all()
            assert len(q_signals) == 6, f"Expected 6 qualified signals persisted in SQLite, found {len(q_signals)}"

            # Print out qualification validation report as requested by the user
            print("\n" + "="*50)
            print("         SIGNAL QUALIFICATION RUN REPORT         ")
            print("="*50)
            print(f"Total Signals Processed : {stats['processed']}")
            print(f"Total Qualified         : {stats['qualified']}")
            print(f"Total Review Required   : {stats['review']}")
            print(f"Total Rejected          : {stats['rejected']}")
            print("-"*50)
            print("Top Rejection Reasons:")
            for reason, count in stats["reasons"].items():
                print(f"  - {reason}: {count}")
            print("-"*50)
            
            print("Sample Qualified Signals:")
            for s in db.query(QualifiedSignal).filter(QualifiedSignal.qualification_status == "QUALIFIED").limit(2).all():
                print(f"  * [{s.source}] {s.sender}: '{s.message}' (Score: {s.qualification_score})")

            print("\nSample Review Signals:")
            for s in db.query(QualifiedSignal).filter(QualifiedSignal.qualification_status == "REVIEW").limit(2).all():
                print(f"  * [{s.source}] {s.sender}: '{s.message}' (Score: {s.qualification_score})")

            print("\nSample Rejected Signals:")
            for s in db.query(QualifiedSignal).filter(QualifiedSignal.qualification_status == "REJECTED").limit(2).all():
                print(f"  * [{s.source}] {s.sender}: '{s.message}' (Score: {s.qualification_score} | Reason: {s.qualification_reason})")
            print("="*50 + "\n")

        logger.success("ALL SIGNAL QUALIFICATION INTEGRATION TESTS PASSED SUCCESSFULLY!")

    finally:
        # Clean up
        db.query(QualifiedSignal).delete()
        db.query(MobileSignal).filter(MobileSignal.device_id == "test_qualify_device").delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_qualification_tests()
