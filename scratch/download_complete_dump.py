import httpx
import json

SUPABASE_URL = "https://tbwnyuampjoamgarwwoo.supabase.co"
BUCKET_NAME = "jarvis-signals"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRid255dWFtcGpvYW1nYXJ3d29vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE5MzUwOTYsImV4cCI6MjA5NzUxMTA5Nn0.3CdCtROBH2l0wq8GVir9_3rWWZUtD9w2UWsz9caM3cg"

def try_download():
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {ANON_KEY}",
    }
    
    # Try different name variations
    filenames = ["complete dump.json", "complete_dump.json"]
    for filename in filenames:
        url = f"{SUPABASE_URL}/storage/v1/object/authenticated/{BUCKET_NAME}/{filename}"
        print(f"Trying download from: {url}")
        res = httpx.get(url, headers=headers, timeout=60.0)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code == 200:
            print("Successfully downloaded!")
            content = res.text
            print(f"Content length in chars: {len(content)}")
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    print("Root JSON type: Dict")
                    print(f"Root keys: {list(data.keys())}")
                    for k, v in data.items():
                        if isinstance(v, list):
                            print(f"  Key '{k}' has list of length: {len(v)}")
                            if len(v) > 0:
                                print(f"  First item preview: {str(v[0])[:300]}")
                elif isinstance(data, list):
                    print("Root JSON type: List")
                    print(f"Length of list: {len(data)}")
                    if len(data) > 0:
                        print(f"First item preview: {str(data[0])[:300]}")
                
                # Write a snippet locally for analysis
                with open("scratch/dump_preview.json", "w") as f:
                    json.dump(data if isinstance(data, list) else data, f, indent=2)
                print("Preview saved to scratch/dump_preview.json")
                return True
            except Exception as e:
                print(f"Failed to parse as JSON: {e}")
                print(f"Beginning of content: {content[:200]}")
                return False
        else:
            print(f"Failed with response: {res.text[:200]}")
            
    print("Could not download file under any variation.")
    return False

if __name__ == "__main__":
    try_download()
