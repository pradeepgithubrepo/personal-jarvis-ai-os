from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.mobile_signal import MobileSignal
from storage.models.signal import Signal

def check():
    db = SessionLocal()
    try:
        total_mobile = db.query(MobileSignal).count()
        unprocessed = db.query(MobileSignal).filter(MobileSignal.processed == False).count()
        processed = db.query(MobileSignal).filter(MobileSignal.processed == True).count()
        signals = db.query(Signal).count()
        
        print(f"Total in mobile_signals: {total_mobile}")
        print(f"  Unprocessed: {unprocessed}")
        print(f"  Processed: {processed}")
        print(f"Total in signals: {signals}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check()
