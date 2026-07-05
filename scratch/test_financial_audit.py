import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal

db = SessionLocal()

results = db.query(UnderstoodSignal, QualifiedSignal).join(
    QualifiedSignal, UnderstoodSignal.qualified_signal_id == QualifiedSignal.id
).all()

count = 0
for u, q in results:
    c = json.loads(u.contract_json)
    if "FINANCIAL" in c.get("classes", []):
        entities = c.get("entities", {})
        monetary = entities.get("monetary_value") if isinstance(entities, dict) else None
        amt = monetary.get("amount") if isinstance(monetary, dict) else None
        if amt is None:
            count += 1
            print(f"[{count}] raw_id={q.signal_id}, qualified_id={q.id}, path={u.processing_path}")
            print(f"  Raw message: {q.message!r}")
            print(f"  Summary: {u.summary!r}")
            print(f"  Entities in contract: {json.dumps(entities, indent=2)}")
            print("-" * 50)
db.close()
