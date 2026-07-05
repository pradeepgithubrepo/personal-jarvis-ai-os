import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.understood_signal import UnderstoodSignal

db = SessionLocal()
u = db.query(UnderstoodSignal).filter(UnderstoodSignal.raw_signal_id == "587").first()
if u:
    print(json.dumps(json.loads(u.contract_json), indent=2))
else:
    print("Not found")
db.close()
