# scratch/debug_endpoint.py

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL") + "/rest/v1/"
headers = {"apikey": os.getenv("SUPABASE_KEY")}
res = requests.get(url, headers=headers).json()

with open("scratch/keys.txt", "w") as f:
    f.write(f"Keys: {list(res.keys())}\n")
    if "swagger" in res or "openapi" in res:
         f.write(f"Info: {res.get('info')}\n")
         f.write(f"Paths: {list(res.get('paths', {}).keys())[:10]}\n")
         f.write(f"Definitions keys: {list(res.get('definitions', {}).keys())[:10]}\n")
    else:
         f.write(f"Raw body snippet: {str(res)[:500]}\n")
