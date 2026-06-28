# scratch/debug_paths.py

import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL") + "/rest/v1/"
headers = {"apikey": os.getenv("SUPABASE_SECRET_KEY")}
res = requests.get(url, headers=headers).json()

with open("scratch/paths.txt", "w") as f:
    f.write(f"Paths: {list(res.get('paths', {}).keys())}\n")
    f.write(f"First path: {json.dumps(res.get('paths', {}), indent=2)[:1000]}\n")
