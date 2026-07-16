import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

signal_ids = [
    9710, 9881, 9731, 9187, 8856, 9005, 9013, 8904, 8989, 9642,
    9641, 8879, 9644, 9046, 9027, 9683, 9014, 9033, 9380, 9102,
    8906, 9219, 8874
]

res = client.table("understood_signals").select("raw_signal_id, signal_type, confidence, summary").in_("raw_signal_id", signal_ids).execute()

print(f"Results for V2.2 updates on the 23 audit signals (Count: {len(res.data)}):")
for r in sorted(res.data, key=lambda x: x["raw_signal_id"]):
    print(f"Signal ID: {r['raw_signal_id']} -> Type: {r['signal_type']} (Confidence: {r['confidence']}) - Summary: {r['summary']}")
