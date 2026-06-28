# scratch/write_counts.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

with open("scratch/db_counts.txt", "w") as f:
    for table in ['signals', 'mobile_signals', 'qualified_signals', 'understood_signals', 'todo_items', 'fyi_events', 'daily_briefs']:
        try:
            cnt = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            f.write(f"{table}: {cnt}\n")
        except Exception as e:
            f.write(f"{table}: Error: {e}\n")

db.close()
