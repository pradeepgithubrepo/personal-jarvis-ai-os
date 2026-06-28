# scratch/check_gaps.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal

db = SessionLocal()

qualified_ids = {s.id for s in db.query(QualifiedSignal).all()}
understood_qualified_ids = {s.qualified_signal_id for s in db.query(UnderstoodSignal).all()}

missing = qualified_ids - understood_qualified_ids

print(f"Total Qualified Signals: {len(qualified_ids)}")
print(f"Total Understood Signals: {len(understood_qualified_ids)}")
print(f"Missing (never understood): {len(missing)}")
if missing:
    print(f"Sample missing IDs: {list(missing)[:5]}")

db.close()
