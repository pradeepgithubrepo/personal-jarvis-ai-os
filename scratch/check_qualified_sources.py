import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from collections import Counter

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

res = client.table("qualified_signals").select("source").eq("qualification_status", "QUALIFIED").execute()
sources = Counter(r["source"] for r in res.data)
print("Qualified sources breakdown:", dict(sources))
