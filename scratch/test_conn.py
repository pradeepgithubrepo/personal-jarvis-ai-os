import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("SUPABASE_DB_URL")

try:
    print("Testing connection with 3s timeout...")
    # Add connect_timeout to the connection string
    if "?" in db_url:
        conn_str = f"{db_url}&connect_timeout=3"
    else:
        conn_str = f"{db_url}?connect_timeout=3"
        
    conn = psycopg2.connect(conn_str)
    print("Connected successfully!")
    conn.close()
except Exception as e:
    print(f"Connection Failed: {e}")
