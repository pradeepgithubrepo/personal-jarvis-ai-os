"""
scripts/run_financial_migration.py

Applies the Phase 3B Financial Agent SQL migration to the remote Supabase instance.
Reads sql/migrations/phase3b_financial_agent.sql and executes it via the Supabase
postgres REST connection.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_financial_migration.py
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIGRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sql", "migrations", "phase3b_financial_agent.sql"
)


def main():
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)

    print(f"Connecting to Supabase: {supabase_url[:40]}...")
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    print(f"Reading migration: {MIGRATION_FILE}")
    with open(MIGRATION_FILE, "r") as f:
        sql = f.read()

    # Split on statement boundaries and execute each individually
    # Supabase REST does not support multi-statement execution in one call
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    print(f"Executing {len(statements)} SQL statements...")
    success = 0
    skipped = 0
    failed = 0

    for i, stmt in enumerate(statements, 1):
        try:
            # Use the postgres RPC endpoint for raw SQL
            result = client.rpc("exec_sql", {"query": stmt + ";"}).execute()
            print(f"  [{i}/{len(statements)}] OK")
            success += 1
        except Exception as e:
            err = str(e)
            if "already exists" in err or "duplicate" in err.lower():
                print(f"  [{i}/{len(statements)}] SKIP (already exists): {stmt[:60]}...")
                skipped += 1
            else:
                print(f"  [{i}/{len(statements)}] FAIL: {err[:120]}")
                print(f"    Statement: {stmt[:100]}...")
                failed += 1

    print(f"\nMigration complete: {success} OK | {skipped} skipped | {failed} failed")

    if failed > 0:
        print("WARNING: Some statements failed. Check output above.")
        sys.exit(1)

    # Verify tables exist
    print("\nVerifying tables...")
    for table in ["financial_transactions", "transaction_evidence", "merchant_normalization_rules"]:
        try:
            res = client.table(table).select("*").limit(1).execute()
            print(f"  ✓ {table} — accessible")
        except Exception as e:
            print(f"  ✗ {table} — ERROR: {e}")


if __name__ == "__main__":
    main()
