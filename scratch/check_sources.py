import json
from collections import Counter

def check_sources():
    with open("scratch/dump_preview.json", "r") as f:
        data = json.load(f)
    
    signals = data.get("signals", [])
    sources = [s.get("source") for s in signals]
    
    print("Unique source values:")
    print(Counter(sources))
    
    # Check lowercase/uppercase variations
    sources_lower = [str(s).lower() for s in sources]
    print("\nUnique case-insensitive source values:")
    print(Counter(sources_lower))

if __name__ == "__main__":
    check_sources()
