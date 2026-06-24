# scratch/view_signals_rich.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.signal import Signal

initialize_database()
session = SessionLocal()

print("Recent 15 signals in DB:")
signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(15).all()

for s in signals:
    print(f"ID: {s.id} | Type: {s.signal_type} | Cat: {s.category} | Imp: {s.importance} | Summary: {s.summary} | Raw: {s.raw_json[:100] if s.raw_json else 'None'}")

session.close()
