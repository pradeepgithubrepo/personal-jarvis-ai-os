"""
scripts/run_lifecycle_migration.py

Applies the Phase 3C Lifecycle Agent SQL migration to the remote Supabase instance.
Reads sql/migrations/phase3c_lifecycle_agent.sql and executes it via the Supabase
postgres REST connection.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_lifecycle_migration.py
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIGRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sql", "migrations", "phase3c_lifecycle_agent.sql"
)


def main():
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)

    print(f"Connecting to Postgres DB: {supabase_url[:40]}...")
    import psycopg2
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not set in environment.")
        sys.exit(1)

    print(f"Reading migration: {MIGRATION_FILE}")
    with open(MIGRATION_FILE, "r") as f:
        sql = f.read()

    print("Connecting directly to PostgreSQL...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cursor:
            # Execute the whole migration SQL script
            cursor.execute(sql)
        conn.close()
        print("Migration applied successfully via direct database connection!")
    except Exception as e:
        print(f"ERROR executing migration: {e}")
        sys.exit(1)

    # Verify tables exist using Supabase client
    print("\nVerifying tables via Supabase client...")
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client_verify: Client = create_client(supabase_url, supabase_key, options=options)
    for table in ["lifecycle_items", "tasks"]:
        try:
            res = client_verify.table(table).select("*").limit(1).execute()
            print(f"  ✓ {table} — accessible")
        except Exception as e:
            print(f"  ✗ {table} — ERROR: {e}")


if __name__ == "__main__":
    main()
