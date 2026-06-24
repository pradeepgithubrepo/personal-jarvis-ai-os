# scratch/cleanup_all_data.py

import os
import sys
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from services.supabase_repo import supabase

def cleanup_local():
    logger.info("Cleaning up local SQLite database...")
    db = SessionLocal()
    try:
        # We delete all records from SQLite tables
        from storage.models.mobile_signal import MobileSignal
        from storage.models.signal import Signal
        from storage.models.task import Task
        from storage.models.todo import Todo
        from storage.models.financial_event import FinancialEvent
        from storage.models.fyi_event import FyiEvent
        from storage.models.processed_file import ProcessedFile
        from storage.models.classification_cache import ClassificationCache
        
        db.query(MobileSignal).delete()
        db.query(Signal).delete()
        db.query(Task).delete()
        db.query(Todo).delete()
        db.query(FinancialEvent).delete()
        db.query(FyiEvent).delete()
        db.query(ProcessedFile).delete()
        db.query(ClassificationCache).delete()
        
        db.commit()
        logger.success("Successfully cleaned up local SQLite database tables.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clean up local SQLite database: {e}")
    finally:
        db.close()

def cleanup_remote():
    logger.info("Cleaning up remote Supabase database tables...")
    
    tables_and_ids = {
        "monthly_category_trends": "trend_id",
        "monthly_category_spend": "entry_id",
        "monthly_spending_summary": "summary_id",
        "financial_transaction_classification": "transaction_id",
        "financial_events": "financial_event_id",
        "fyi_events": "fyi_event_id",
        "todos": "todo_id",
        "facts": "fact_id",
        "signals": "signal_id",
        "processed_files": "file_name"
    }
    
    for table, id_col in tables_and_ids.items():
        try:
            logger.info(f"Clearing Supabase table '{table}'...")
            if id_col == "file_name":
                supabase.table(table).delete().neq(id_col, "dummy_non_existent_file").execute()
            else:
                supabase.table(table).delete().neq(id_col, "00000000-0000-0000-0000-000000000000").execute()
            logger.success(f"Cleared table '{table}'.")
        except Exception as e:
            logger.error(f"Failed to clear table '{table}': {e}")

if __name__ == "__main__":
    cleanup_local()
    cleanup_remote()
    logger.success("Clean slate database cleanup complete.")
