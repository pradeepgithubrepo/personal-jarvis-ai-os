# scripts/run_todo_extraction.py

import os
import sys
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.todo import Todo
from services.signal_processor import SignalProcessor


def run_extraction():
    logger.info("Initializing database...")
    initialize_database()

    logger.info("Starting TODO extraction...")
    extracted_count = SignalProcessor.extract_todos()
    logger.success(f"TODO extraction run complete. Extracted {extracted_count} new tasks.")

    db = SessionLocal()
    try:
        todos = db.query(Todo).all()
        
        print("\n" + "="*60)
        print("                 TODO DATABASE STATISTICS")
        print("="*60)
        print(f"Total TODO Tasks: {len(todos)}")
        
        if not todos:
            print("No TODO tasks found in database.")
            return

        print("\n" + "-"*60)
        print("                    ALL TODO RECORDS")
        print("-"*60)
        for i, t in enumerate(todos):
            print(f"#{i+1}: {t.title}")
            print(f"    Due: {t.due_date} | Priority: {t.priority} | Signal ID: {t.source_signal_id}")
        print("="*60 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    run_extraction()
