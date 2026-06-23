import os
import sys
import json

# Ensure python path includes project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from storage.models.signal import Signal
from storage.models.mobile_signal import MobileSignal
from storage.models.signal_classification import SignalClassification

def check_signals():
    session = SessionLocal()
    try:
        # Query whatsapp signals
        whatsapp_signals = session.query(Signal).filter(Signal.source == "whatsapp").all()
        print(f"Total WhatsApp signals in 'signals' table: {len(whatsapp_signals)}")
        
        print("\n--- WHATSAPP SIGNALS CLASSIFICATION ---")
        for i, sig in enumerate(whatsapp_signals, 1):
            # Try to parse raw JSON details
            details = {}
            if sig.raw_json:
                try:
                    details = json.loads(sig.raw_json)
                except Exception:
                    pass
            
            sender = details.get("sender") or sig.signal_type or "Unknown"
            message = details.get("message") or sig.summary or ""
            
            # Fetch specific classification if exists
            classification = session.query(SignalClassification).filter(SignalClassification.signal_id == sig.id).first()
            class_category = classification.category if classification else sig.category
            confidence = classification.confidence if classification else 1.0
            
            print(f"\n[{i}] ID: {sig.id}")
            print(f"    Sender:         {sender}")
            print(f"    Message:        {message}")
            print(f"    Summary:        {sig.summary}")
            print(f"    LLM Category:   {class_category} (confidence: {confidence:.2f})")
            print(f"    Importance:     {sig.importance}")
            print(f"    Created At:     {sig.created_at}")

        # Also let's check mobile_signals
        mobile_signals = session.query(MobileSignal).filter(MobileSignal.source == "whatsapp").all()
        print(f"\nTotal WhatsApp signals in 'mobile_signals' table: {len(mobile_signals)}")
        if mobile_signals:
            print("\n--- MOBILE WHATSAPP SIGNALS ---")
            for i, msig in enumerate(mobile_signals, 1):
                print(f"[{i}] Sender: {msig.sender} | Msg: {msig.message[:60]} | Created At: {msig.created_at}")

    except Exception as e:
        print(f"Error querying database: {e}", file=sys.stderr)
    finally:
        session.close()

if __name__ == "__main__":
    check_signals()
