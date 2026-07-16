import os
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

print("Deleting all rows from signal_routes...")
client.table("signal_routes").delete().neq("id", str(uuid.uuid4())).execute()

print("Deleting all rows from understood_signals...")
client.table("understood_signals").delete().neq("id", str(uuid.uuid4())).execute()

print("Deleting all rows from qualified_signals...")
client.table("qualified_signals").delete().neq("id", str(uuid.uuid4())).execute()

print("Resetting processed flag in mobile_signals...")
# Postgrest doesn't support bulk update without filters, so we do eq("processed", True)
client.table("mobile_signals").update({"processed": False}).eq("processed", True).execute()

print("Database cleared successfully via HTTP!")
