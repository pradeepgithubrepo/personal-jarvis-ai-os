import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.understood_signal import UnderstoodSignal

db = SessionLocal()
s = db.query(UnderstoodSignal).filter(UnderstoodSignal.id == "75daddd5-5831-5363-a785-daba6a0ecbc4").first()
if s:
    print(f"Type: {type(s.contract_json)}")
    print(f"Value: {s.contract_json!r}")
else:
    print("Not found")
db.close()
