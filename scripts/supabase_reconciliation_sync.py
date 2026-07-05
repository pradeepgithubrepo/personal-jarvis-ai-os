# scripts/supabase_reconciliation_sync.py

import sys
import os
import json
from datetime import datetime
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.supabase_repo import supabase

db = SessionLocal()

TABLE_PK_MAP = {
    "bank_accounts": "id",
    "financial_events": "id",
    "financial_facts": "id",
    "merchant_profiles": "id",
    "merchants": "id",
    "mobile_signals": "id",
    "monthly_category_spend": "entry_id",
    "monthly_category_trends": "trend_id",
    "monthly_spending_summary": "summary_id",
    "pipeline_runs": "run_id",
    "qualified_signals": "id",
    "runtime_events": "id",
    "salary_events": "id",
    "salary_sources": "id",
    "signals": "id",
    "transfer_pairs": "id",
    "daily_briefs": "brief_id",
    "facts": "fact_id",
    "todo_items": "todo_id",
    "fyi_events": "event_id",
    "understood_signals": "id",
    "processed_files": "file_id",
    "system_status": "system_name",
    "fact_relationships": "id"
}

def remove_null_bytes(val):
    if isinstance(val, str):
        return val.replace("\u0000", "")
    elif isinstance(val, dict):
        return {k: remove_null_bytes(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [remove_null_bytes(x) for x in val]
    return val

def clean_record(row_dict, table):
    """Clean record datatypes for Supabase REST ingestion."""
    cleaned = {}
    for k, v in row_dict.items():
        v = remove_null_bytes(v)
        # Handle datetime strings
        if isinstance(v, datetime):
            cleaned[k] = v.isoformat()
        # Handle UUIDs
        elif isinstance(v, uuid.UUID):
            cleaned[k] = str(v)
        # Handle JSON/JSONB string serialization
        elif k in ["sender_aliases", "receiver_aliases", "aliases", "metadata", "fact_value", "evidence", "source_reference", "contract_json"]:
            if isinstance(v, str):
                try:
                    cleaned[k] = json.loads(v)
                except Exception:
                    cleaned[k] = v
            else:
                cleaned[k] = v
        else:
            cleaned[k] = v

    if table == "todo_items":
        why = cleaned.pop("why_action_needed", "")
        cons = cleaned.pop("consequence_if_ignored", "")
        desc = cleaned.get("description") or ""
        if why:
            desc = f"{desc}\nWhy Action Needed: {why}"
        if cons:
            desc = f"{desc}\nConsequence if Ignored: {cons}"
        cleaned["description"] = desc.strip()

    return cleaned

def sync_table(table):
    pk = TABLE_PK_MAP.get(table)
    if not pk:
        print(f"Skipping table {table} (No primary key mapped).")
        return

    print(f"\n--- Synchronizing table: {table} ---")

    # 1. Fetch remote records primary keys
    try:
        remote_res = supabase.table(table).select(pk).execute()
        remote_keys = {str(r[pk]) for r in (remote_res.data or []) if r.get(pk) is not None}
    except Exception as e:
        print(f"Error reading remote {table}: {e}")
        return

    # 2. Fetch local SQLite records
    try:
        # Get column names
        cols_res = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        cols = [c[1] for c in cols_res]
        
        local_rows = db.execute(text(f"SELECT * FROM {table}")).fetchall()
    except Exception as e:
        print(f"Error reading local SQLite {table}: {e}")
        return

    missing_records = []
    for row in local_rows:
        row_dict = dict(zip(cols, row))
        
        local_pk_val = row_dict.get(pk)
        if str(local_pk_val) not in remote_keys:
            cleaned = clean_record(row_dict, table)
            
            # Remove autoincrement integer IDs for BIGSERIAL tables if needed
            if table in ["mobile_signals", "qualified_signals", "runtime_events", "processed_files", "fact_relationships"] and "id" in cleaned:
                # Let Postgres generate the BigSerial ID
                cleaned.pop("id", None)
                
            missing_records.append(cleaned)

    print(f"Found {len(local_rows)} local records, {len(remote_keys)} remote records. Missing to sync: {len(missing_records)}")

    # 3. Batch insert missing records
    if missing_records:
        batch_size = 100
        for i in range(0, len(missing_records), batch_size):
            batch = missing_records[i:i+batch_size]
            try:
                supabase.table(table).upsert(batch).execute()
                print(f"Successfully migrated batch {i//batch_size + 1} ({len(batch)} records) to Supabase.")
            except Exception as e:
                print(f"Error inserting/upserting batch: {e}")
    else:
        print("Table is already in sync.")

if __name__ == "__main__":
    tables_to_sync = [
        "bank_accounts", "financial_events", "financial_facts", "merchant_profiles", 
        "merchants", "mobile_signals", "monthly_category_spend", "monthly_category_trends", 
        "monthly_spending_summary", "pipeline_runs", "qualified_signals", "runtime_events", 
        "salary_events", "salary_sources", "signals", "transfer_pairs",
        "daily_briefs", "facts", "fact_relationships", "todo_items", "fyi_events", 
        "understood_signals", "processed_files", "system_status"
    ]
    for table in tables_to_sync:
        sync_table(table)
        
    print("\nReconciliation Sync complete!")
    db.close()
