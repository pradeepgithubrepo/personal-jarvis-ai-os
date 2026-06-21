# tests/test_financial_extractor.py

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
from storage.models.financial_event import FinancialEvent
from services.signal_processor import SignalProcessor


def run_financial_extractor_tests():
    logger.info("Initializing database schema...")
    initialize_database()

    db = SessionLocal()
    try:
        # 1. Clean up old test data
        logger.info("Cleaning up old test data...")
        db.query(FinancialEvent).delete()
        db.query(SignalClassification).delete()
        db.query(Signal).filter(
            (Signal.summary.like("%[TEST_FIN_EXT]%")) | (Signal.summary.like("%[TEST_SIG_PROC]%"))
        ).delete(synchronize_session=False)
        db.commit()

        # 2. Add mock signals
        logger.info("Inserting mock financial signals...")
        base_time = datetime(2026, 6, 21, 12, 0, 0)

        # Case 1: Debit UPI payment with amount inside raw json
        sig_debit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_FIN_EXT] Rs 450.00 debited from account for Zomato order.",
            raw_json=json.dumps({
                "amount": "450.00",
                "currency": "INR",
                "transaction_type": "debit",
                "paid_to": "Zomato",
                "payment_channel": "UPI",
                "transaction_id": "TXN889900"
            }),
            created_at=base_time
        )

        # Case 2: Credit Alert with amount inside text summary only
        sig_credit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_FIN_EXT] Salary of INR 95,000 credited to your bank account.",
            raw_json=json.dumps({
                "currency": "INR",
                "paid_from": "ACME Corp",
                "payment_channel": "Bank Transfer"
            }),
            created_at=base_time
        )

        # Case 3: Insurance Renewal (should map to 'renewal')
        sig_insurance = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="high",
            summary="[TEST_FIN_EXT] Policy renewal premium of Rs.5,200.00 is due for your bike insurance.",
            raw_json=json.dumps({
                "amount": "Rs.5,200.00",
                "currency": "INR"
            }),
            created_at=base_time
        )

        db.add(sig_debit)
        db.add(sig_credit)
        db.add(sig_insurance)
        db.commit()

        debit_id = sig_debit.id
        credit_id = sig_credit.id
        insurance_id = sig_insurance.id

        # 3. Classify first
        logger.info("Classifying mock signals...")
        SignalProcessor.process_all_signals()

        c_debit = db.query(SignalClassification).get(debit_id)
        c_credit = db.query(SignalClassification).get(credit_id)
        c_insurance = db.query(SignalClassification).get(insurance_id)

        assert c_debit.category == "FINANCIAL", f"Expected FINANCIAL, got {c_debit.category}"
        assert c_credit.category == "FINANCIAL", f"Expected FINANCIAL, got {c_credit.category}"
        assert c_insurance.category == "INSURANCE", f"Expected INSURANCE, got {c_insurance.category}"

        # 4. Extract financial events
        logger.info("Running extract_financial_events()...")
        extracted_count = SignalProcessor.extract_financial_events()
        assert extracted_count >= 3, f"Expected at least 3 extracted financial events, got {extracted_count}"

        # 5. Verify database records
        db.expire_all()

        event_debit = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == debit_id).first()
        assert event_debit is not None
        assert event_debit.amount == 450.0
        assert event_debit.transaction_type == "debit"
        assert event_debit.payment_channel == "UPI"
        assert event_debit.paid_to == "Zomato"
        assert event_debit.transaction_id == "TXN889900"

        event_credit = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == credit_id).first()
        assert event_credit is not None
        assert event_credit.amount == 95000.0, f"Expected 95000.0, got {event_credit.amount}"
        assert event_credit.transaction_type == "credit"
        assert event_credit.paid_from == "ACME Corp"
        assert event_credit.payment_channel == "Bank Transfer"

        event_insurance = db.query(FinancialEvent).filter(FinancialEvent.source_signal_id == insurance_id).first()
        assert event_insurance is not None
        assert event_insurance.amount == 5200.0, f"Expected 5200.0, got {event_insurance.amount}"
        assert event_insurance.transaction_type == "renewal"

        # 6. Verify duplicate prevention
        logger.info("Re-running extract_financial_events() to verify duplicate prevention...")
        second_run_count = SignalProcessor.extract_financial_events()
        assert second_run_count == 0, f"Expected 0 new extractions on second run, got {second_run_count}"

        # 7. Test parse_amount utility directly
        assert SignalProcessor.parse_amount("1,500.00") == 1500.0
        assert SignalProcessor.parse_amount("Rs. 450") == 450.0
        assert SignalProcessor.parse_amount("INR 95,000.50") == 95000.5
        assert SignalProcessor.parse_amount("$250") == 250.0
        assert SignalProcessor.parse_amount(None) is None
        assert SignalProcessor.parse_amount(100) == 100.0

        logger.success("ALL FINANCIAL EXTRACTOR INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"Financial extractor integration tests failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_financial_extractor_tests()
