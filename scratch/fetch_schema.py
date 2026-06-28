# scratch/fetch_schema.py

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL") + "/rest/v1/"
headers = {
    "apikey": os.getenv("SUPABASE_SECRET_KEY"),
    "Accept-Profile": "jarvis_insights_schema"
}
res = requests.get(url, headers=headers).json()

# Write the definitions (tables & column schemas) to a file
with open("scratch/supabase_schema.json", "w") as f:
    json.dump(res.get("definitions", {}), f, indent=2)

print("Schema successfully fetched and saved to scratch/supabase_schema.json")
