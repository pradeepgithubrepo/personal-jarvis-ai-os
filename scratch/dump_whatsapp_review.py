import os
import csv
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

# Query all WhatsApp signals in qualified_signals with status = REVIEW
res = client.table("qualified_signals").select("id, signal_id, sender, message, timestamp, qualification_score, qualification_reason").eq("source", "whatsapp").eq("qualification_status", "REVIEW").execute()

csv_columns = [
    "id",
    "signal_id",
    "sender",
    "message",
    "timestamp",
    "qualification_score",
    "qualification_reason",
    "pradeep review comments - yes / no"
]

csv_path = "docs/v2/understanding_layer/WHATSAPP_REVIEW_DUMP.csv"
os.makedirs(os.path.dirname(csv_path), exist_ok=True)

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    for row in res.data:
        # Construct row with empty column for user pass
        writer.writerow({
            "id": row.get("id"),
            "signal_id": row.get("signal_id"),
            "sender": row.get("sender"),
            "message": row.get("message"),
            "timestamp": row.get("timestamp"),
            "qualification_score": row.get("qualification_score"),
            "qualification_reason": row.get("qualification_reason"),
            "pradeep review comments - yes / no": ""
        })

print(f"Dumped {len(res.data)} WhatsApp REVIEW signals to {csv_path}")
