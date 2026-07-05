# scratch/reset_consumer_tracking.py

import sys
import os
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.supabase_repo import supabase

db = SessionLocal()

print("Backing up processed_files table to docs/processed_files_backup.csv...")
rows = db.execute(text("SELECT * FROM processed_files")).fetchall()
cols = ["id", "file_name", "bucket_name", "file_path", "file_hash", "status", "created_at"]

os.makedirs("docs", exist_ok=True)
with open("docs/processed_files_backup.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(cols)
    for r in rows:
        writer.writerow(list(r))
print("✔ Backup complete.")

print("Clearing local processed_files...")
db.execute(text("DELETE FROM processed_files"))
db.commit()
print("✔ Local processed_files cleared.")

print("Clearing remote Supabase processed_files...")
try:
    supabase.table("processed_files").delete().neq("file_path", "nonexistent").execute()
    print("✔ Remote processed_files cleared.")
except Exception as e:
    print(f"✘ Failed to clear remote processed_files: {e}")

db.close()
