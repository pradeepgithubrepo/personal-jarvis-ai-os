import os
import sys
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL environment variable is missing.")
        sys.exit(1)

    migration_file = "sql/migrations/phase3a_todo_agent.sql"
    if not os.path.exists(migration_file):
        print(f"Error: Migration file not found at {migration_file}")
        sys.exit(1)

    print(f"Reading migration file {migration_file}...")
    with open(migration_file, "r") as f:
        sql = f.read()

    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("Executing SQL migration DDL...")
            cur.execute(sql)
        conn.close()
        print("SQL migration executed successfully!")
    except Exception as e:
        print(f"Failed to execute migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
