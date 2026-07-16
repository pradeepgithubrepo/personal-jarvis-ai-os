import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

count_us = client.table('understood_signals').select('count', count='exact').limit(0).execute().count
res = client.table("understood_signals").select("processing_path").execute()
from collections import Counter
paths = Counter(r["processing_path"] for r in res.data)

print(f"Current count of understood_signals: {count_us}")
print(f"Processing paths breakdown: {dict(paths)}")
