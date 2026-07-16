import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("SUPABASE_DB_URL")

if not db_url:
    print("Error: SUPABASE_DB_URL is not set.")
    exit(1)

try:
    print("Connecting to database to check active backends...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Query current processes
    cursor.execute("""
        SELECT pid, query, state, age(clock_timestamp(), query_start) 
        FROM pg_stat_activity 
        WHERE state != 'idle' AND pid != pg_backend_pid();
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} active queries:")
    for row in rows:
        print(f"  PID: {row[0]}, Query: {row[1][:100]}, State: {row[2]}, Age: {row[3]}")
        
    # Terminate backend connections to clear locks
    cursor.execute("""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE pid != pg_backend_pid() 
          AND usename = 'postgres';
    """)
    terminated = cursor.fetchall()
    print(f"Terminated {len(terminated)} backends to clear locks.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error terminating backends: {e}")
