import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

# Select all understood signals processed via fallback path
res = client.table("understood_signals").select("id, signal_type, confidence, summary, contract_json, processing_path, qualified_signals(source, sender, message)").eq("processing_path", "fallback").execute()

print(f"Total fallback signals: {len(res.data)}")
sources = {}
type_counts = {}

detailed_records = []

for row in res.data:
    qs = row.get("qualified_signals") or {}
    source = qs.get("source", "unknown")
    sender = qs.get("sender", "unknown")
    msg = qs.get("message", "")
    sig_type = row.get("signal_type")
    
    sources[source] = sources.get(source, 0) + 1
    type_counts[sig_type] = type_counts.get(sig_type, 0) + 1
    
    detailed_records.append({
        "source": source,
        "sender": sender,
        "message": msg,
        "signal_type": sig_type,
        "summary": row.get("summary"),
        "contract": row.get("contract_json")
    })

print("Sources breakdown:", sources)
print("Types breakdown:", type_counts)

# Let's save the first 50 detailed records as a JSON file to inspect
with open("scratch/unstructured_audit.json", "w") as f:
    json.dump(detailed_records, f, indent=2)
print("Saved details to scratch/unstructured_audit.json")
