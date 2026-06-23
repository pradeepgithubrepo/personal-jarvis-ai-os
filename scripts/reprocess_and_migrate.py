# scripts/reprocess_and_migrate.py

import os
import sys
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.todo import Todo
from storage.models.financial_event import FinancialEvent
from storage.models.fyi_event import FyiEvent
from storage.models.signal_classification import SignalClassification
from services.signal_processor import SignalProcessor

def reprocess():
    logger.info("Initializing database...")
    initialize_database()
    
    db = SessionLocal()
    try:
        # Clear old classifications and extractions in SQLite to force re-running
        logger.info("Clearing SQLite classifications and extractions to prepare for re-run...")
        db.query(SignalClassification).delete()
        db.query(Todo).delete()
        db.query(FinancialEvent).delete()
        db.query(FyiEvent).delete()
        db.commit()
        logger.success("SQLite clean complete.")
    finally:
        db.close()

    # Run the classification and extraction pipeline
    logger.info("Step 1: Classifying all signals...")
    classified = SignalProcessor.process_all_signals()
    logger.success(f"Classified {classified} signals.")

    logger.info("Step 2: Extracting and loading Todos to Postgres...")
    todos = SignalProcessor.extract_todos()
    logger.success(f"Extracted {todos} Todos.")

    logger.info("Step 3: Extracting and loading Financial Events to Postgres...")
    financials = SignalProcessor.extract_financial_events()
    logger.success(f"Extracted {financials} Financial Events.")

    logger.info("Step 4: Extracting and loading FYI Events to Postgres...")
    fyis = SignalProcessor.extract_fyi_events()
    logger.success(f"Extracted {fyis} FYI Events.")

    logger.success("Reprocessing and migration run complete!")

if __name__ == "__main__":
    reprocess()
