import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("SUPABASE_DB_URL")

if not db_url:
    print("Error: SUPABASE_DB_URL is not set.")
    exit(1)

sql_script = """
BEGIN;
TRUNCATE TABLE jarvis_insights_schemav1.signal_routes CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.understood_signals CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.qualified_signals CASCADE;
UPDATE jarvis_insights_schemav1.mobile_signals SET processed = false;
COMMIT;
"""

try:
    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Truncating tables and resetting processed flag...")
    cursor.execute(sql_script)
    print("Done!")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
