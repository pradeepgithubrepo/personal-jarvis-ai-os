# scratch/view_signals.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.mobile_signal import MobileSignal

initialize_database()
session = SessionLocal()

ids = [917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930]
for idx in ids:
    sig = session.query(MobileSignal).filter(MobileSignal.id == idx).first()
    if sig:
        print(f"ID: {sig.id} | Source: {sig.source} | Sender: {sig.sender} | Message: {sig.message}")
    else:
        print(f"ID: {idx} | Not found")

session.close()
