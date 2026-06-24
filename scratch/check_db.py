# scratch/check_db.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.mobile_signal import MobileSignal
from storage.models.classification_cache import ClassificationCache
from storage.models.signal import Signal

initialize_database()
session = SessionLocal()

print("MobileSignal count:")
print("  Total:", session.query(MobileSignal).count())
print("  Processed:", session.query(MobileSignal).filter(MobileSignal.processed == True).count())
print("  Unprocessed:", session.query(MobileSignal).filter(MobileSignal.processed == False).count())

print("\nClassificationCache count:", session.query(ClassificationCache).count())
print("\nSignal count:", session.query(Signal).count())

print("\nSample classification cache:")
for c in session.query(ClassificationCache).limit(5).all():
    print(f"Key: {c.cache_key}, Result: {c.result_json[:200]}")

session.close()
