import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

res = client.table("understood_signals").select("*").limit(1).execute()
if res.data:
    print("Columns:", list(res.data[0].keys()))
else:
    # Try fetching table definition using PostgreSQL via HTTP
    # (Since Postgrest returns empty list if no data, we can query a view or schema details if we can)
    print("Table is empty. Let's check if we can query schema details...")
