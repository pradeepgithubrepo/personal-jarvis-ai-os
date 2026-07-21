"""
scripts/run_vault_migration.py

Applies the Phase 3D Vault Module SQL migration to the remote Supabase PostgreSQL instance.
Reads sql/migrations/phase3d_vault_module.sql and executes it.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_vault_migration.py
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIGRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sql", "migrations", "phase3d_vault_module.sql"
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

    print("Connecting directly to PostgreSQL DB...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(sql)
        conn.close()
        print("✓ Migration executed successfully via direct DB connection!")
    except Exception as e:
        print(f"ERROR executing migration SQL: {e}")
        sys.exit(1)

    # Verify tables and display loaded vault entries
    print("\nVerifying database tables and fetching loaded entries...")
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    try:
        cat_res = client.table("vault_categories").select("*").order("display_order").execute()
        categories = cat_res.data
        print(f"  ✓ vault_categories — {len(categories)} categories active")

        entry_res = client.table("vault_entries").select("*, vault_categories(category_name)").order("sort_order").execute()
        entries = entry_res.data
        print(f"  ✓ vault_entries — {len(entries)} entries loaded successfully!\n")

        print(f"{'Cat Name':<18} | {'Owner':<8} | {'Title':<30} | {'Sub Category':<20} | {'Location / Platform':<25} | {'Access / Where':<20} | {'Documents / Storage'}")
        print("-" * 150)
        for entry in entries:
            cat_name = entry.get("vault_categories", {}).get("category_name") if entry.get("vault_categories") else ""
            owner = entry.get("owner", "")
            title = entry.get("title", "")
            sub_cat = entry.get("sub_category") or ""
            location = entry.get("location") or ""
            access_info = entry.get("access_information") or ""
            notes = entry.get("notes") or ""
            print(f"{cat_name:<18} | {owner:<8} | {title:<30} | {sub_cat:<20} | {location:<25} | {access_info:<20} | {notes}")

    except Exception as e:
        print(f"ERROR verifying table contents: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
