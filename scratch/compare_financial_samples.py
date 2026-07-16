import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(url, key, options=options)

sample_ids = [
    "58c8d57f-aaba-4710-87c6-a00bfcbb2d18",
    "fd2e3d77-8654-4f44-8ba1-87dd058126b0",
    "4996820b-05ac-42ce-8266-db85b9a02df1",
    "298c4a32-c67e-4c12-bc12-f6978a11c346",
    "48364238-fa5e-4cc6-81da-bd864d377ab8",
    "0c21b17b-f9ff-4882-a051-fe7717ce391e",
    "5d6c79c3-3ef2-44f4-8e63-125384c4f678",
    "1db259ee-1520-4602-9653-17388e80eb7a",
    "45d6fa90-4b51-432c-bd47-15e65f675250",
    "3688ff1d-c539-40b2-af1e-80721fe1c001"
]

res = client.table("understood_signals").select("*, mobile_signals:raw_signal_id(*)").in_("id", sample_ids).execute()

for idx, row in enumerate(res.data):
    print(f"--- SAMPLE {idx+1} ---")
    print(f"Understood ID: {row['id']}")
    print(f"Summary: {row['summary']}")
    print(f"Contract: {json.dumps(row['contract_json'], indent=2)}")
    
    ms = row.get("mobile_signals")
    if ms:
        print(f"Source Signal ID: {ms['id']}")
        print(f"Source Sender: {ms['sender']}")
        print(f"Source Type: {ms['source']}")
        print(f"Source Message: {ms['message']}")
        print(f"Source Timestamp: {ms['mobile_timestamp']}")
    else:
        print("Source Signal not found.")
    print()
