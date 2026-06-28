import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from storage.models.understood_signal import UnderstoodSignal

def main():
    db = SessionLocal()
    rows = db.query(UnderstoodSignal).all()
    print(f"Total understood signals in DB: {len(rows)}")
    for row in rows[:30]:  # print first 30 to understand the schema
        contract = json.loads(row.contract_json)
        print(f"US.id={row.id} | US.qualified_signal_id={row.qualified_signal_id} | Contract signal_id={contract.get('signal_id')} | Summary='{contract.get('summary')}'")
    db.close()

if __name__ == "__main__":
    main()
