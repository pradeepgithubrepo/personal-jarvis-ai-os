"""
scripts/run_daily_briefing_migration.py

Applies the Phase 3E Daily Briefing Agent SQL migration to the remote Supabase instance.
Reads sql/migrations/phase3e_daily_briefing_agent.sql and executes it.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_daily_briefing_migration.py
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIGRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sql", "migrations", "phase3e_daily_briefing_agent.sql"
)


def main():
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    db_url = os.environ.get("SUPABASE_DB_URL")

    if not supabase_url or not supabase_key or not db_url:
        print("ERROR: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or SUPABASE_DB_URL not set.")
        sys.exit(1)

    print(f"Reading migration file: {MIGRATION_FILE}")
    with open(MIGRATION_FILE, "r") as f:
        sql = f.read()

    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    # 1. Try Supabase rpc exec_sql execution
    print("Executing SQL migration via Supabase RPC...")
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    success = False
    try:
        for stmt in statements:
            client.rpc("exec_sql", {"query": stmt + ";"}).execute()
        print("✓ Migration executed successfully via Supabase RPC!")
        success = True
    except Exception as rpc_err:
        print(f"RPC exec_sql warning: {rpc_err}. Falling back to psycopg2 connection...")

    if not success and db_url:
        try:
            conn = psycopg2.connect(db_url, connect_timeout=5)
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.close()
            print("✓ Migration executed successfully via direct DB connection!")
        except Exception as db_err:
            print(f"Direct DB connection warning: {db_err}")

    # Verify daily_briefings table via Supabase client
    print("\nVerifying daily_briefings table via Supabase client...")
    try:
        res = client.table("daily_briefings").select("*").limit(1).execute()
        print("  ✓ daily_briefings — accessible and ready!")
    except Exception as e:
        print(f"  ✗ daily_briefings — ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
