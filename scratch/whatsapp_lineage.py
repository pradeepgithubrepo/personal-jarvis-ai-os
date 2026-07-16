import os
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from collections import Counter

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

# 1. Total WhatsApp signals in mobile_signals
res_ms = client.table("mobile_signals").select("id").eq("source", "whatsapp").execute()
total_ms = len(res_ms.data)

# 2. WhatsApp signals in qualified_signals with status
res_qs = client.table("qualified_signals").select("qualification_status, qualification_reason, message").eq("source", "whatsapp").execute()
qs_statuses = Counter(r["qualification_status"] for r in res_qs.data)
qs_reasons = Counter(r["qualification_reason"] for r in res_qs.data)

# 3. WhatsApp signals in understood_signals
res_us_join = client.table("understood_signals").select("id, qualified_signals(source)").execute()
total_us = sum(1 for row in res_us_join.data if row.get("qualified_signals", {}).get("source") == "whatsapp")

print(f"Total WhatsApp signals in mobile_signals: {total_ms}")
print(f"WhatsApp qualification status breakdown: {dict(qs_statuses)}")
print(f"WhatsApp qualification reason breakdown: {dict(qs_reasons)}")
print(f"Total WhatsApp signals in understood_signals: {total_us}")

# Let's inspect a sample of REJECTED WhatsApp messages
rejected_samples = [r for r in res_qs.data if r["qualification_status"] == "REJECTED"][:10]
print("\nSample Rejected WhatsApp Messages:")
for idx, r in enumerate(rejected_samples):
    print(f"{idx+1}. Reason: {r['qualification_reason']}")
    print(f"   Message: {r['message'][:120]}...")
