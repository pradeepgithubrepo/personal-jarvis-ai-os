# scripts/remediation_sqlite_migration.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

LINEAGE_TABLES = [
    "mobile_signals", "qualified_signals", "understood_signals", 
    "financial_facts", "facts", "todo_items", "fyi_events", "daily_briefs"
]

print("Applying SQLite schema remediation...")

# 1. Add columns to core tables if they do not exist
for table in LINEAGE_TABLES:
    # Check existing columns
    cols_res = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
    existing_cols = [c[1] for c in cols_res]
    
    if "batch_id" not in existing_cols:
        db.execute(text(f"ALTER TABLE {table} ADD COLUMN batch_id TEXT;"))
        print(f"Added batch_id to {table}")
    if "sync_status" not in existing_cols:
        db.execute(text(f"ALTER TABLE {table} ADD COLUMN sync_status VARCHAR(50) DEFAULT 'SYNCED';"))
        print(f"Added sync_status to {table}")
    if "is_deleted" not in existing_cols:
        db.execute(text(f"ALTER TABLE {table} ADD COLUMN is_deleted BOOLEAN DEFAULT 0;"))
        print(f"Added is_deleted to {table}")
    if "deleted_at" not in existing_cols:
        db.execute(text(f"ALTER TABLE {table} ADD COLUMN deleted_at DATETIME;"))
        print(f"Added deleted_at to {table}")

# 2. Create ingestion_batches table
db.execute(text("""
CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id TEXT PRIMARY KEY,
    source_type TEXT,
    source_name TEXT,
    file_name TEXT,
    file_hash TEXT,
    status TEXT,
    raw_records INTEGER,
    accepted_records INTEGER,
    duplicate_records INTEGER,
    rejected_records INTEGER,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""))
print("Created ingestion_batches table")

# 3. Create sync_metadata table
db.execute(text("""
CREATE TABLE IF NOT EXISTS sync_metadata (
    entity_name TEXT PRIMARY KEY,
    last_pull_time DATETIME,
    last_push_time DATETIME,
    last_success_time DATETIME,
    sync_status TEXT,
    updated_at DATETIME
);
"""))
print("Created sync_metadata table")

# 4. Create sync_audit_log table
db.execute(text("""
CREATE TABLE IF NOT EXISTS sync_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT,
    record_id TEXT,
    batch_id TEXT,
    operation TEXT,
    status TEXT,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""))
print("Created sync_audit_log table")

db.commit()
print("SQLite migration complete!")
db.close()
