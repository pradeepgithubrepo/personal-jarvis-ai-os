# scratch/audit_supabase.py

import os
import sys
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("SUPABASE_DB_URL")
if not db_url:
    print("Error: SUPABASE_DB_URL not found in environment.")
    sys.exit(1)

try:
    import psycopg2
    conn = psycopg2.connect(db_url)
except ImportError:
    try:
        import psycopg
        conn = psycopg.connect(db_url)
    except ImportError:
        print("Neither psycopg2 nor psycopg is installed. Installing psycopg2-binary...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2
        conn = psycopg2.connect(db_url)

cursor = conn.cursor()

# Query Phase 1: list all tables in jarvis_insights_schema
print("=== TABLES IN jarvis_insights_schema ===")
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'jarvis_insights_schema' 
    ORDER BY table_name;
""")
tables = cursor.fetchall()
for t in tables:
    print(t[0])

# Query Phase 2: list all columns in jarvis_insights_schema
print("\n=== COLUMNS IN jarvis_insights_schema ===")
cursor.execute("""
    SELECT table_name, column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_schema = 'jarvis_insights_schema' 
    ORDER BY table_name, ordinal_position;
""")
columns = cursor.fetchall()
for col in columns:
    print(f"Table: {col[0]} | Column: {col[1]} | Type: {col[2]} | Nullable: {col[3]}")

# Query Constraints
print("\n=== CONSTRAINTS IN jarvis_insights_schema ===")
cursor.execute("""
    SELECT tc.table_name, tc.constraint_name, tc.constraint_type, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    WHERE tc.table_schema = 'jarvis_insights_schema'
    ORDER BY tc.table_name, tc.constraint_name;
""")
constraints = cursor.fetchall()
for c in constraints:
    print(f"Table: {c[0]} | Constraint: {c[1]} | Type: {c[2]} | Column: {c[3]}")

cursor.close()
conn.close()
