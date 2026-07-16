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
    
    # Query REVIEW signals
    res = client.table("qualified_signals").select("message, sender, source, qualification_reason").eq("qualification_status", "REVIEW").limit(30).execute()
    print("REVIEW SIGNALS:")
    for idx, row in enumerate(res.data):
        print(f"{idx+1}. Sender: {row.get('sender')} | Source: {row.get('source')} | Reason: {row.get('qualification_reason')}")
        print(f"   Msg: {row.get('message')}")
        print("-" * 40)

if __name__ == "__main__":
    main()
