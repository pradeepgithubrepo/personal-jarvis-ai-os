# scratch/check_db.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

processed = db.execute(text("SELECT COUNT(*) FROM mobile_signals WHERE processed = 1")).scalar()
pending = db.execute(text("SELECT COUNT(*) FROM mobile_signals WHERE processed = 0")).scalar()
total = db.execute(text("SELECT COUNT(*) FROM mobile_signals")).scalar()

print(f"Total Mobile Signals: {total}")
print(f"Processed (Archived): {processed}")
print(f"Pending: {pending}")

db.close()
