import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.understood_signal import UnderstoodSignal

db = SessionLocal()
signals = db.query(UnderstoodSignal).limit(10).all()
for s in signals:
    print(f"ID={s.id}, qualified_signal_id={s.qualified_signal_id}, raw_signal_id={s.raw_signal_id}, path={s.processing_path}")
db.close()
