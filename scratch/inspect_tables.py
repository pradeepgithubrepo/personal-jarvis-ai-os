import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
opts = ClientOptions(schema="jarvis_insights_schemav1")
client = create_client(url, key, options=opts)

print("Columns of mobile_signals:")
res = client.table("mobile_signals").select("*").limit(1).execute()
print(res.data[0].keys() if res.data else "No data")

print("\nColumns of qualified_signals:")
res = client.table("qualified_signals").select("*").limit(1).execute()
print(res.data[0].keys() if res.data else "No data")

print("\nColumns of understood_signals:")
res = client.table("understood_signals").select("*").limit(1).execute()
print(res.data[0].keys() if res.data else "No data")

print("\nColumns of signal_routes:")
res = client.table("signal_routes").select("*").limit(1).execute()
print(res.data[0].keys() if res.data else "No data")
