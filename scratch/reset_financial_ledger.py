import os
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    db_url = os.environ.get("SUPABASE_DB_URL")

    if not db_url:
        print("Error: SUPABASE_DB_URL is not set.")
        exit(1)

    sql_script = """
    BEGIN;
    TRUNCATE TABLE jarvis_insights_schemav1.transaction_evidence CASCADE;
    TRUNCATE TABLE jarvis_insights_schemav1.financial_transactions CASCADE;
    
    UPDATE jarvis_insights_schemav1.signal_routes 
    SET route_status = 'PENDING', completed_at = NULL, error_message = NULL
    WHERE agent_name = 'financial_agent';
    COMMIT;
    """

    try:
        print("Connecting to Supabase Database...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Resetting financial ledger tables and routes...")
        cursor.execute(sql_script)
        print("Financial reset complete!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Reset Failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
