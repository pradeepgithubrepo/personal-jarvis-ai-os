import json

def main():
    with open("scratch/full_analysis_breakdown.json") as f:
        data = json.load(f)
    
    ignored = [d for d in data if d["outcome"] == "DROPPED (IGNORED)"]
    print(f"Total ignored signals: {len(ignored)}")
    for i, d in enumerate(ignored):
        print(f"{i+1}. Route ID: {d['route_id']}")
        print(f"   Message: {d['message'].strip()}")
        print(f"   Route Reason: {d['route_reason']}")
        print("-" * 80)

if __name__ == "__main__":
    main()
