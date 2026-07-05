# scratch/cleanup_consumer_data.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.supabase_repo import supabase

TABLES = [
    "mobile_signals", "qualified_signals", "understood_signals",
    "financial_facts", "facts", "todo_items", "fyi_events", "daily_briefs"
]

db = SessionLocal()

print("Cleaning SQLite tables...")
for table in TABLES:
    db.execute(text(f"DELETE FROM {table}"))
db.commit()
print("✔ SQLite tables cleared.")

print("Cleaning remote Supabase tables...")
PK_MAP = {
    "mobile_signals": "id",
    "qualified_signals": "id",
    "understood_signals": "id",
    "financial_facts": "id",
    "facts": "fact_id",
    "todo_items": "todo_id",
    "fyi_events": "event_id",
    "daily_briefs": "brief_id"
}

for table in TABLES:
    pk = PK_MAP[table]
    try:
        if pk == "id":
            # For integer bigint/bigserial, we can filter neq on a string that represents nonexistence or integer
            supabase.table(table).delete().neq(pk, -1).execute()
        else:
            supabase.table(table).delete().neq(pk, "nonexistent").execute()
        print(f"✔ Supabase table '{table}' cleared.")
    except Exception as e:
        print(f"✘ Failed to clear Supabase table '{table}': {e}")

db.close()
