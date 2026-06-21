# scratch/inspect_signals.py

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.signal import Signal

def main():
    db = SessionLocal()
    try:
        signals = db.query(Signal).all()
        print(f"Total signals: {len(signals)}")
        
        sources = Counter(s.source for s in signals)
        categories = Counter(s.category for s in signals)
        types = Counter(s.signal_type for s in signals)
        importances = Counter(s.importance for s in signals)
        
        print("\nSources:")
        for k, v in sources.items():
            print(f"  {k}: {v}")
            
        print("\nCategories:")
        for k, v in categories.items():
            print(f"  {k}: {v}")
            
        print("\nSignal Types:")
        for k, v in types.items():
            print(f"  {k}: {v}")
            
        print("\nImportances:")
        for k, v in importances.items():
            print(f"  {k}: {v}")
            
        print("\nSamples:")
        for s in signals[:20]:
            print(f"[{s.source}] [{s.category}] [{s.signal_type}] [{s.importance}] -> {s.summary[:80]}...")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
