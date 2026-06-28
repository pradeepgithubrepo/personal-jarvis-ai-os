# scratch/debug_endpoint_secret.py

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL") + "/rest/v1/"
headers = {"apikey": os.getenv("SUPABASE_SECRET_KEY")}
res = requests.get(url, headers=headers).json()

with open("scratch/keys_secret.txt", "w") as f:
    f.write(f"Keys: {list(res.keys())}\n")
    if "swagger" in res or "openapi" in res:
         f.write(f"Paths count: {len(res.get('paths', {}))}\n")
         f.write(f"Definitions keys: {list(res.get('definitions', {}).keys())}\n")
    else:
         f.write(f"Raw body: {str(res)[:1000]}\n")
