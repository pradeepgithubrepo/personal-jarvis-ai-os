# scratch/get_sqlite_ddl.py

import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# List of tables we want to align
tables = [
    "signals", "mobile_signals", "qualified_signals", "understood_signals",
    "financial_events", "financial_facts", "salary_events", "salary_sources",
    "merchant_profiles", "bank_accounts", "merchants", "runtime_events",
    "transfer_pairs", "facts", "fact_relationships", "todo_items", "fyi_events",
    "daily_briefs", "monthly_spending_summary", "monthly_category_spend",
    "monthly_category_trends"
]

print("Generating Postgres DDL...")

postgres_ddl = []
postgres_ddl.append("CREATE SCHEMA IF NOT EXISTS jarvis_insights_schema;")
postgres_ddl.append("SET search_path TO jarvis_insights_schema;")

for table in tables:
    # Get SQLite CREATE statement
    sql_res = db.execute(text(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")).fetchone()
    if not sql_res:
        print(f"Table {table} not found in SQLite.")
        continue
    
    sqlite_sql = sql_res[0]
    
    # Translate SQLite dialect to PostgreSQL
    pg_sql = sqlite_sql
    # Replace table name to include schema
    pg_sql = pg_sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE IF NOT EXISTS jarvis_insights_schema.{table}")
    pg_sql = pg_sql.replace(f"CREATE TABLE \"{table}\"", f"CREATE TABLE IF NOT EXISTS jarvis_insights_schema.{table}")
    
    # Types
    pg_sql = pg_sql.replace("INTEGER PRIMARY KEY", "BIGSERIAL PRIMARY KEY")
    pg_sql = pg_sql.replace("DATETIME", "TIMESTAMPTZ")
    pg_sql = pg_sql.replace("DATE", "DATE")
    pg_sql = pg_sql.replace("BOOLEAN", "BOOLEAN")
    pg_sql = pg_sql.replace("FLOAT", "NUMERIC")
    pg_sql = pg_sql.replace("JSON", "JSONB")
    
    # Remove foreign key constraints that might block table drops/creates
    # We will define simple columns, and add foreign keys later or let them slide for flat tables
    # Clean up column definitions
    lines = pg_sql.split("\n")
    cleaned_lines = []
    for line in lines:
        if "FOREIGN KEY" in line:
            # Skip SQLite-style foreign keys for flat schema migration
            continue
        cleaned_lines.append(line)
    
    pg_sql = "\n".join(cleaned_lines)
    
    # Strip trailing commas if any line was removed
    pg_sql = re.sub(r',\s*\n\s*\)', '\n)', pg_sql)
    
    postgres_ddl.append(f"DROP TABLE IF EXISTS jarvis_insights_schema.{table} CASCADE;")
    postgres_ddl.append(pg_sql + ";\n")

# Write to file
with open("sql/recreate_all_supabase_tables.sql", "w") as f:
    f.write("\n".join(postgres_ddl))

print("PostgreSQL DDL successfully written to sql/recreate_all_supabase_tables.sql")
db.close()
