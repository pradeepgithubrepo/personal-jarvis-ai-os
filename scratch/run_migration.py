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

-- 1. TRUNCATE DOWNSTREAM TABLES (FK CASCADE)
TRUNCATE TABLE jarvis_insights_schemav1.signal_routes CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.understood_signals CASCADE;
TRUNCATE TABLE jarvis_insights_schemav1.qualified_signals CASCADE;

-- 2. ALTER TABLE SCHEMA
ALTER TABLE jarvis_insights_schemav1.qualified_signals
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS message_hash TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB,
ADD COLUMN IF NOT EXISTS amount NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS currency VARCHAR(3),
ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(10);

-- 3. ADD CONSTRAINTS
ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP CONSTRAINT IF EXISTS qualified_signals_message_hash_key,
ADD CONSTRAINT qualified_signals_message_hash_key UNIQUE (message_hash);

ALTER TABLE jarvis_insights_schemav1.qualified_signals
DROP CONSTRAINT IF EXISTS check_tx_type,
ADD CONSTRAINT check_tx_type CHECK (transaction_type IN ('DEBIT', 'CREDIT'));

-- 4. RESET PROCESS FLAG ON INGESTED MOBILE SIGNALS
UPDATE jarvis_insights_schemav1.mobile_signals
SET processed = false;

COMMIT;
"""

try:
    print("Connecting to Supabase Database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Executing Migration SQL...")
    cursor.execute(sql_script)
    print("Migration executed successfully!")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Migration Failed: {e}")
    exit(1)
