# scratch/run_recon_audit.py

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.supabase_repo import supabase

db = SessionLocal()

# List SQLite Tables
print("=== SQLite Tables ===")
tables_res = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
sqlite_tables = [r[0] for r in tables_res if not r[0].startswith("sqlite_")]

sqlite_inventory = {}
for table in sqlite_tables:
    try:
        cnt = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        
        # Columns info
        cols_res = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        cols = [{"name": c[1], "type": c[2], "nullable": not c[3], "pk": bool(c[5])} for c in cols_res]
        
        # Date range
        created_range = ("N/A", "N/A")
        updated_range = ("N/A", "N/A")
        
        col_names = [c["name"] for c in cols]
        if "created_at" in col_names and cnt > 0:
            min_c = db.execute(text(f"SELECT MIN(created_at) FROM {table}")).scalar()
            max_c = db.execute(text(f"SELECT MAX(created_at) FROM {table}")).scalar()
            created_range = (str(min_c), str(max_c))
        if "updated_at" in col_names and cnt > 0:
            min_u = db.execute(text(f"SELECT MIN(updated_at) FROM {table}")).scalar()
            max_u = db.execute(text(f"SELECT MAX(updated_at) FROM {table}")).scalar()
            updated_range = (str(min_u), str(max_u))
            
        sqlite_inventory[table] = {
            "count": cnt,
            "columns": cols,
            "created_range": created_range,
            "updated_range": updated_range
        }
        print(f"SQLite Table: {table} | Count: {cnt}")
    except Exception as e:
        print(f"Error on SQLite Table {table}: {e}")

# Read Supabase OpenAPI Swagger Schema Cache
print("\n=== Supabase Tables (From REST spec) ===")
with open("scratch/supabase_schema.json") as f:
    supabase_defs = json.load(f)

supabase_inventory = {}
for table, schema in sorted(supabase_defs.items()):
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    cols = []
    for col, props in properties.items():
        cols.append({
            "name": col,
            "type": props.get("type"),
            "format": props.get("format", ""),
            "nullable": col not in required
        })
        
    # Get remote count
    cnt = 0
    created_range = ("N/A", "N/A")
    updated_range = ("N/A", "N/A")
    try:
        # Check if table exists by selecting 1 record
        res = supabase.table(table).select("*").execute()
        data = res.data or []
        cnt = len(data)
        
        if cnt > 0:
            # Sort by created_at if present
            col_names = [c["name"] for c in cols]
            if "created_at" in col_names:
                dates = [d["created_at"] for d in data if d.get("created_at")]
                if dates:
                    created_range = (min(dates), max(dates))
            if "updated_at" in col_names:
                dates = [d["updated_at"] for d in data if d.get("updated_at")]
                if dates:
                    updated_range = (min(dates), max(dates))
    except Exception as e:
        print(f"Error querying Supabase table {table}: {e}")
        
    supabase_inventory[table] = {
        "count": cnt,
        "columns": cols,
        "created_range": created_range,
        "updated_range": updated_range
    }
    print(f"Supabase Table: {table} | Count: {cnt}")

# Save results
with open("scratch/recon_data.json", "w") as f:
    json.dump({
        "sqlite": sqlite_inventory,
        "supabase": supabase_inventory
    }, f, indent=2)

print("\nSaved reconciliation inventory to scratch/recon_data.json")
db.close()
