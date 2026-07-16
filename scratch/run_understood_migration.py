import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("SUPABASE_DB_URL")

if not db_url:
    print("Error: SUPABASE_DB_URL is not set.")
    exit(1)

# Let's test standard ports or try connecting
# If the db_url uses port 443, we can also try swapping it to 5432 or 6543 if it fails.
ports_to_try = [None] # None means use port from db_url
if ":443/" in db_url:
    ports_to_try.append(5432)
    ports_to_try.append(6543)

sql_script = """
BEGIN;

-- 1. ADD device_id, message_hash, AND metadata JSONB COLUMNS
ALTER TABLE jarvis_insights_schemav1.understood_signals
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS message_hash TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 2. ADD UNIQUE CONSTRAINT ON qualified_signal_id (ENFORCES STRICT 1:1 RELATION)
ALTER TABLE jarvis_insights_schemav1.understood_signals
DROP CONSTRAINT IF EXISTS understood_signals_qualified_signal_id_key,
ADD CONSTRAINT understood_signals_qualified_signal_id_key UNIQUE (qualified_signal_id);

-- 3. ADD UNIQUE CONSTRAINT ON message_hash (ENFORCES CONTRACT IDEMPOTENCY)
ALTER TABLE jarvis_insights_schemav1.understood_signals
DROP CONSTRAINT IF EXISTS understood_signals_message_hash_key,
ADD CONSTRAINT understood_signals_message_hash_key UNIQUE (message_hash);

COMMIT;
"""

success = False
for port in ports_to_try:
    try:
        current_url = db_url
        if port is not None:
            current_url = db_url.replace(":443/", f":{port}/")
        
        # Add connection timeout
        if "?" in current_url:
            conn_str = f"{current_url}&connect_timeout=3"
        else:
            conn_str = f"{current_url}?connect_timeout=3"
            
        print(f"Connecting to database using url: {conn_str.split('@')[-1]} ...")
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Executing migration SQL...")
        cursor.execute(sql_script)
        print("DDL Migration completed successfully!")
        cursor.close()
        conn.close()
        success = True
        break
    except Exception as e:
        print(f"Failed connection/execution: {e}")

if not success:
    print("MIGRATION_FAILED: Direct database connection failed on all ports.")
    print("Please fire the DDL manually in the Supabase SQL editor.")
    exit(1)
