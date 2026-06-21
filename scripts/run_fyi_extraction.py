# scripts/run_fyi_extraction.py

import os
import sys
from collections import Counter
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.fyi_event import FyiEvent
from services.signal_processor import SignalProcessor


def run_extraction():
    logger.info("Initializing database...")
    initialize_database()

    logger.info("Starting FYI extraction...")
    extracted_count = SignalProcessor.extract_fyi_events()
    logger.success(f"FYI extraction run complete. Extracted {extracted_count} new events.")

    db = SessionLocal()
    try:
        events = db.query(FyiEvent).all()
        
        print("\n" + "="*60)
        print("                 FYI EVENTS STATISTICS")
        print("="*60)
        print(f"Total FYI Events: {len(events)}")
        
        if not events:
            print("No FYI events found in database.")
            return

        # 1. Distribution by Type
        types = [e.fyi_type for e in events]
        print("\n1. Distribution by FYI Type:")
        for ftype, count in sorted(Counter(types).items()):
            print(f"  - {ftype.upper()}: {count}")

        # 2. Sample Output
        print("\n" + "-"*60)
        print("                     FYI EVENT SAMPLES")
        print("-"*60)
        # Show up to 15 samples
        for i, e in enumerate(events[:15]):
            print(f"#{i+1}: {e.title[:90]}...")
            print(f"    Type: {e.fyi_type} | Content: {e.content[:90] if e.content else ''}")
            print(f"    Signal ID: {e.source_signal_id} | Created: {e.created_at}")
        print("="*60 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    run_extraction()
