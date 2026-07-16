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

# Query qualified_signals by signal_id
res_qs = client.table("qualified_signals").select("id, signal_id, source, sender, message, qualification_status, qualification_reason").in_("signal_id", signal_ids).execute()

# Query understood_signals by raw_signal_id
res_us = client.table("understood_signals").select("raw_signal_id, signal_type, confidence, summary, contract_json, processing_path").in_("raw_signal_id", signal_ids).execute()

us_map = {row["raw_signal_id"]: row for row in res_us.data}
qs_map = {row["signal_id"]: row for row in res_qs.data}

results = []
for sid in signal_ids:
    qs_row = qs_map.get(sid, {})
    us_row = us_map.get(sid, {})
    
    results.append({
        "signal_id": sid,
        "source": qs_row.get("source", "unknown"),
        "sender": qs_row.get("sender", "unknown"),
        "message": qs_row.get("message", "N/A"),
        "qualification_status": qs_row.get("qualification_status", "N/A"),
        "qualification_reason": qs_row.get("qualification_reason", "N/A"),
        "predicted_type": us_row.get("signal_type", "N/A"),
        "confidence": us_row.get("confidence", "N/A"),
        "summary": us_row.get("summary", "N/A"),
        "contract": us_row.get("contract_json", {}),
        "processing_path": us_row.get("processing_path", "N/A")
    })

import json
with open("scratch/rca_signals_data.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Fetched {len(results)} signals for RCA analysis.")
