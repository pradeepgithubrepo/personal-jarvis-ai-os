# scripts/run_financial_extraction.py

import os
import sys
from collections import Counter
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.financial_event import FinancialEvent
from services.signal_processor import SignalProcessor


def run_extraction():
    logger.info("Initializing database...")
    initialize_database()

    logger.info("Starting financial extraction...")
    extracted_count = SignalProcessor.extract_financial_events()
    logger.success(f"Financial extraction run complete. Extracted {extracted_count} new events.")

    db = SessionLocal()
    try:
        events = db.query(FinancialEvent).all()
        
        print("\n" + "="*60)
        print("              FINANCIAL EVENTS STATISTICS")
        print("="*60)
        print(f"Total Financial Events: {len(events)}")
        
        if not events:
            print("No financial events found in database.")
            return

        # 1. Distribution by Type
        types = [e.transaction_type for e in events]
        print("\n1. Distribution by Transaction Type:")
        for ttype, count in sorted(Counter(types).items()):
            print(f"  - {ttype.upper()}: {count}")

        # 2. Sample Output
        print("\n" + "-"*60)
        print("                  FINANCIAL EVENT SAMPLES")
        print("-"*60)
        # Show up to 15 samples
        for i, e in enumerate(events[:15]):
            print(f"#{i+1}: {e.title[:90]}...")
            print(f"    Amount: {e.amount} {e.currency} | Type: {e.transaction_type} | Date: {e.event_date}")
            print(f"    Paid To: {e.paid_to} | Paid From: {e.paid_from} | Txn ID: {e.transaction_id}")
        print("="*60 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    run_extraction()
