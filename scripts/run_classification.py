# scripts/run_classification.py

import os
import sys
from collections import Counter
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from services.signal_processor import SignalProcessor


def run_classification():
    logger.info("Initializing database...")
    initialize_database()

    logger.info("Starting Signal Classification run...")
    processed_count = SignalProcessor.process_all_signals()
    logger.success(f"Signal Classification run complete. Processed {processed_count} signals.")

    db = SessionLocal()
    try:
        classifications = db.query(SignalClassification).all()
        signals = {s.id: s for s in db.query(Signal).all()}
        
        print("\n" + "="*60)
        print("          SIGNAL CLASSIFICATION STATISTICS")
        print("="*60)
        print(f"Total Classified Signals: {len(classifications)}")
        
        if not classifications:
            print("No classified signals found.")
            return

        # 1. Distribution by Category
        categories = [c.category for c in classifications]
        print("\n1. Distribution by Classified Category:")
        for cat, count in sorted(Counter(categories).items()):
            print(f"  - {cat}: {count}")

        # 2. Classified Samples
        print("\n" + "-"*60)
        print("                 CLASSIFIED SAMPLES BY CATEGORY")
        print("-"*60)
        
        by_category = {}
        for c in classifications:
            by_category.setdefault(c.category, []).append(c)
            
        for cat, list_c in sorted(by_category.items()):
            print(f"\nCategory: {cat} (Total: {len(list_c)})")
            # Show up to 5 samples per category
            for i, c in enumerate(list_c[:5]):
                sig = signals.get(c.signal_id)
                if sig:
                    print(f"  Sample #{i+1}: Source: {sig.source} | Summary: {sig.summary[:90]}... (Confidence: {c.confidence})")
                else:
                    print(f"  Sample #{i+1}: Signal ID {c.signal_id} not found in database! (Confidence: {c.confidence})")
        print("="*60 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    run_classification()
