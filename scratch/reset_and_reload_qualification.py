import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(url, key, options=options)
    
    print("Clearing qualified_signals table...")
    # Delete all rows from qualified_signals by filtering neq to a dummy UUID
    try:
        res = client.table("qualified_signals").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"Clear qualified_signals completed.")
    except Exception as e:
        print(f"Error clearing qualified_signals: {e}")
        sys.exit(1)
    
    print("Resetting processed flag to False in mobile_signals...")
    try:
        # Update rows where processed = True
        res = client.table("mobile_signals").update({"processed": False}).eq("processed", True).execute()
        print(f"Reset processed flag in mobile_signals completed.")
    except Exception as e:
        print(f"Error resetting mobile_signals: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
