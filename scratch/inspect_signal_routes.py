import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

# Select one row from signal_routes if it exists, or fetch columns from information_schema via RPC or raw query if we had it,
# but we can also just fetch a sample or do a select of columns.
res = client.table("signal_routes").select("*").limit(1).execute()
print("Sample signal_routes columns:", res.data[0].keys() if res.data else "No rows in signal_routes yet")
