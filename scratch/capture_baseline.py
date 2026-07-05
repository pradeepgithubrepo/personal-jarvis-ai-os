# scratch/capture_baseline.py

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

print("Capturing row counts...")
baseline_counts = {}
for table in TABLES:
    sqlite_count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    
    try:
        supabase_res = supabase.table(table).select("count", count="exact").execute()
        supabase_count = supabase_res.count
    except Exception as e:
        supabase_count = f"Error: {e}"
        
    baseline_counts[table] = (sqlite_count, supabase_count)

print("Capturing date-wise breakdown...")
date_breakdown = []
# SQLite date wise query
sqlite_dates = db.execute(text("""
    SELECT
        DATE(mobile_timestamp) as d,
        COUNT(*) as c
    FROM mobile_signals
    GROUP BY d
    ORDER BY d
""")).fetchall()

# Generate Markdown
md = []
md.append("# Pre-Reload Baseline Capture\n")
md.append("## Table Row Counts\n")
md.append("| Table Name | Local SQLite Count | Remote Supabase Count |")
md.append("| --- | --- | --- |")
for table, (sql_cnt, sup_cnt) in baseline_counts.items():
    md.append(f"| {table} | {sql_cnt} | {sup_cnt} |")

md.append("\n## Date-wise Breakdown of Raw Signals (SQLite)\n")
md.append("| Date | Signal Count |")
md.append("| --- | --- |")
for row in sqlite_dates:
    md.append(f"| {row[0] or 'NULL'} | {row[1]} |")

os.makedirs("docs", exist_ok=True)
with open("docs/pre_reload_baseline.md", "w") as f:
    f.write("\n".join(md))

print("Baseline captured and saved to docs/pre_reload_baseline.md")
db.close()
