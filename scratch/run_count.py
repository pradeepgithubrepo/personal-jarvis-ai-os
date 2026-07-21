import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

load_dotenv()
client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"], options=ClientOptions(schema="jarvis_insights_schemav1"))

tx_res = client.table("financial_transactions").select("transaction_id", count="exact").limit(1).execute()
ev_res = client.table("transaction_evidence").select("evidence_id", count="exact").limit(1).execute()

print(f"financial_transactions count: {tx_res.count}")
print(f"transaction_evidence count: {ev_res.count}")
