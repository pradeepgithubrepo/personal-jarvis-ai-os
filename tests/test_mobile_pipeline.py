# tests/test_mobile_pipeline.py

import sys
import os
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.mobile_signal import MobileSignal
from storage.models.signal import Signal
from storage.models.task import Task
from services.mobile_signal_pipeline import MobileSignalPipeline


def run_pipeline_test():
    logger.info("Initializing database and schema...")
    initialize_database()

    import datetime
    start_time = datetime.datetime.utcnow()
    
    db = SessionLocal()
    try:
        # Clear existing test data
        db.query(MobileSignal).filter(
            (MobileSignal.device_id.like("test_pipeline_%")) | (MobileSignal.device_id == "test_device_1")
        ).delete(synchronize_session=False)
        db.query(Signal).filter(
            (Signal.summary.like("%[TEST_PIPELINE]%")) | (Signal.summary.like("%Hello Jarvis%"))
        ).delete(synchronize_session=False)
        db.query(Signal).filter(Signal.raw_json.like("%1500%")).delete(synchronize_session=False)
        db.query(Task).filter(Task.title.like("%[TEST_PIPELINE]%")).delete(synchronize_session=False)
        db.commit()

        logger.info("Inserting mock mobile signals...")
        
        # 1. Financial transaction SMS
        sig_finance = MobileSignal(
            device_id="test_pipeline_phone",
            source="sms",
            sender="HDFCBank",
            message="[TEST_PIPELINE] ALERT: UPI transaction of INR 1500.00 spent on Zomato from HDFC card ending 1234. Ref: 67890",
            mobile_timestamp="1782021845000",
            processed=False
        )
        
        # 2. Personal WhatsApp chat message
        sig_chat = MobileSignal(
            device_id="test_pipeline_phone",
            source="whatsapp",
            sender="Shobana",
            message="[TEST_PIPELINE] Did you bring the grocery items?",
            mobile_timestamp="1782021846000",
            processed=False
        )
        
        # 3. WhatsApp system noise notification
        sig_noise = MobileSignal(
            device_id="test_pipeline_phone",
            source="whatsapp",
            sender="WhatsApp System",
            message="Checking for new messages",
            mobile_timestamp="1782021847000",
            processed=False
        )

        # 4. SMS OTP message
        sig_otp = MobileSignal(
            device_id="test_pipeline_phone",
            source="sms",
            sender="998877",
            message="[TEST_PIPELINE] Your one-time verification password code is 887755. Use within 10 minutes.",
            mobile_timestamp="1782021848000",
            processed=False
        )

        db.add(sig_finance)
        db.add(sig_chat)
        db.add(sig_noise)
        db.add(sig_otp)
        db.commit()

        # Get their IDs
        finance_id = sig_finance.id
        chat_id = sig_chat.id
        noise_id = sig_noise.id
        otp_id = sig_otp.id

        logger.info("Mock signals inserted successfully. Running Mobile Signal Pipeline...")

        # Run pipeline
        pipeline = MobileSignalPipeline()
        pipeline.run()

        # Re-fetch from DB to verify states
        db.expire_all()
        
        # Verify MobileSignals processed flags
        m_finance = db.query(MobileSignal).get(finance_id)
        m_chat = db.query(MobileSignal).get(chat_id)
        m_noise = db.query(MobileSignal).get(noise_id)
        m_otp = db.query(MobileSignal).get(otp_id)

        assert m_finance.processed is True, f"Expected finance signal to be processed, got {m_finance.processed}"
        assert m_chat.processed is True, f"Expected chat signal to be processed, got {m_chat.processed}"
        assert m_noise.processed is True, f"Expected noise signal to be marked processed, got {m_noise.processed}"
        assert m_otp.processed is True, f"Expected OTP signal to be marked processed (noise filtered), got {m_otp.processed}"
        logger.success("Processed flags in mobile_signals table verified!")

        # Verify main signals table insertions (noise & OTP shouldn't be here)
        test_signals = db.query(Signal).filter(Signal.created_at >= start_time).all()
        
        assert len(test_signals) == 2, f"Expected 2 structured signals in this run, found {len(test_signals)}"
        
        sms_signals = [s for s in test_signals if s.source == "sms"]
        whatsapp_signals = [s for s in test_signals if s.source == "whatsapp"]

        assert len(sms_signals) == 1, f"Expected 1 sms signal, got {len(sms_signals)}"
        assert len(whatsapp_signals) == 1, f"Expected 1 whatsapp signal, got {len(whatsapp_signals)}"

        # Verify structured content of financial signal
        f_sig = sms_signals[0]
        assert f_sig.category == "finance"
        assert f_sig.signal_type == "financial_transaction"
        assert f_sig.importance in ("high", "medium", "low", "ignore")
        logger.info(f"Structured raw_json from LLM: {f_sig.raw_json}")

        # Verify structured content of chat signal (WhatsApp personal chat gets high priority)
        c_sig = whatsapp_signals[0]
        assert c_sig.importance == "high", f"Expected high priority for WhatsApp personal chat, got {c_sig.importance}"
        
        import json
        c_details = json.loads(c_sig.raw_json)
        assert "classification" in c_details, "Expected classification field in WhatsApp details"
        assert c_details["classification"] in ("task", "FYI"), f"Expected task or FYI classification, got {c_details['classification']}"
        logger.info(f"Structured chat signal raw_json: {c_sig.raw_json}")

        logger.success("ALL MOBILE PIPELINE INTEGRATION TESTS PASSED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"Pipeline integration test failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_pipeline_test()
