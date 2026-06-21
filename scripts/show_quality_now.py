# scripts/show_quality_now.py

import json
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.signal import Signal

def main():
    db = SessionLocal()
    try:
        signals = db.query(Signal).all()
        print("\n" + "="*60)
        print("          CURRENT QUALITY EVALUATION STATISTICS")
        print("="*60)
        print(f"Total Structured Signals Processed: {len(signals)}")
        
        if not signals:
            print("No structured signals found in database yet.")
            return
            
        # 1. Distribution by Source
        sources = [s.source for s in signals]
        print("\n1. Distribution by Source:")
        for src, count in sorted(Counter(sources).items()):
            print(f"  - {src.upper()}: {count}")
            
        # 2. Distribution by Category
        categories = [s.category for s in signals]
        print("\n2. Distribution by Category:")
        for cat, count in sorted(Counter(categories).items()):
            print(f"  - {cat}: {count}")
            
        # 3. Distribution by Importance/Priority
        importances = [s.importance for s in signals]
        print("\n3. Distribution by Importance/Priority:")
        for imp, count in sorted(Counter(importances).items()):
            print(f"  - {imp}: {count}")

        # 4. Distribution by Signal Type / Intent
        types = [s.signal_type for s in signals]
        print("\n4. Distribution by Intent Type:")
        for stype, count in sorted(Counter(types).items()):
            print(f"  - {stype}: {count}")

        # 5. Output Samples
        print("\n" + "-"*60)
        print("                 STRUCTURED OUTPUT SAMPLES")
        print("-"*60)
        for i, s in enumerate(signals):
            print(f"\nSample #{i+1}: Source = {s.source} | Category = {s.category} | Priority = {s.importance} | Intent = {s.signal_type}")
            print(f"Summary: {s.summary}")
            try:
                details = json.loads(s.raw_json) if s.raw_json else {}
                print(f"Structured Details: {json.dumps(details, indent=2)}")
            except Exception:
                print(f"Raw JSON: {s.raw_json}")
        print("="*60 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
