# scratch/reprocess_filtered_signals.py

import os
import sys
import uuid
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.daily_brief import DailyBrief
from storage.models.monthly_category_trend import MonthlyCategoryTrend
from storage.models.monthly_category_spend import MonthlyCategorySpend
from storage.models.monthly_spending_summary import MonthlySpendingSummary
from storage.models.financial_transaction_classification import FinancialTransactionClassification
from storage.models.fyi_event import FyiEvent
from storage.models.financial_event import FinancialEvent
from storage.models.todo import Todo
from storage.models.signal_classification import SignalClassification
from storage.models.task import Task
from storage.models.signal import Signal
from storage.models.mobile_signal import MobileSignal

from services.system_initializer import initialize_system
from services.mobile_signal_pipeline import MobileSignalPipeline
from services.signal_processor import SignalProcessor
from services.financial_intelligence import FinancialIntelligenceService
from services.financial_aggregator import FinancialAggregator
from services.daily_brief_generator import DailyBriefGenerator
from services.supabase_repo import supabase


def clear_supabase_table(table_name: str, pk_col: str):
    """
    Deletes all rows in a Supabase table by selecting keys that do not match a dummy UUID.
    """
    try:
        logger.info(f"Clearing Supabase table '{table_name}'...")
        res = supabase.table(table_name).delete().neq(pk_col, "00000000-0000-0000-0000-000000000000").execute()
        logger.info(f"Successfully cleared Supabase table '{table_name}'.")
    except Exception as e:
        logger.error(f"Failed to clear Supabase table '{table_name}': {e}")


def main():
    logger.info("=== STARTING FILTERED REPROCESSING PIPELINE ===")
    
    # 1. Initialize system
    logger.info("Initializing system and configurations...")
    initialize_system()

    # 2. Truncate SQLite tables
    logger.info("Truncating SQLite tables...")
    db = SessionLocal()
    try:
        db.query(DailyBrief).delete()
        db.query(MonthlyCategoryTrend).delete()
        db.query(MonthlyCategorySpend).delete()
        db.query(MonthlySpendingSummary).delete()
        db.query(FinancialTransactionClassification).delete()
        db.query(FyiEvent).delete()
        db.query(FinancialEvent).delete()
        db.query(Todo).delete()
        db.query(SignalClassification).delete()
        db.query(Task).delete()
        db.query(Signal).delete()
        db.commit()
        logger.success("Successfully truncated local SQLite database tables.")
    except Exception as e:
        logger.error(f"Failed to clear local SQLite database: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

    # 3. Clean up Supabase tables in order of dependencies
    logger.info("Cleaning up Supabase tables...")
    clear_supabase_table("financial_transaction_classification", "transaction_id")
    clear_supabase_table("todos", "todo_id")
    clear_supabase_table("financial_events", "financial_event_id")
    clear_supabase_table("fyi_events", "fyi_event_id")
    clear_supabase_table("signals", "signal_id")
    clear_supabase_table("monthly_category_trends", "trend_id")
    clear_supabase_table("monthly_category_spend", "entry_id")
    clear_supabase_table("monthly_spending_summary", "summary_id")
    logger.success("Successfully cleaned up all active tables in Supabase.")

    # 4. Setup mobile signals in SQLite: mark available whatsapp + top 500 recent SMS as unprocessed
    logger.info("Configuring mobile_signals processing states...")
    db = SessionLocal()
    try:
        # Mark everything as processed first
        db.query(MobileSignal).update({MobileSignal.processed: True})
        db.commit()

        # Mark all WhatsApp signals as unprocessed
        whatsapp_signals = db.query(MobileSignal).filter(MobileSignal.source == "whatsapp").all()
        for w in whatsapp_signals:
            w.processed = False
            
        # Mark top 500 SMS signals ordered by ID descending as unprocessed
        sms_signals = db.query(MobileSignal).filter(MobileSignal.source == "sms").order_by(MobileSignal.id.desc()).limit(500).all()
        for s in sms_signals:
            s.processed = False

        db.commit()
        logger.success(f"Configured processing status. Marked {len(whatsapp_signals)} WhatsApp signals and {len(sms_signals)} SMS signals as unprocessed (to be reprocessed).")
    except Exception as e:
        logger.error(f"Failed to configure mobile signals table: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

    # 5. Run Mobile Signal Processing Pipeline in loop
    logger.info("Running Mobile Signal Pipeline...")
    pipeline = MobileSignalPipeline()
    batch_idx = 0
    while True:
        db = SessionLocal()
        try:
            unprocessed_count = db.query(MobileSignal).filter(MobileSignal.processed == False).count()
            logger.info(f"Unprocessed mobile signals left: {unprocessed_count}")
            if unprocessed_count == 0:
                break
        finally:
            db.close()

        batch_idx += 1
        logger.info(f"Executing pipeline batch {batch_idx}...")
        pipeline.run()

    # 6. Classify signals
    logger.info("Running signal classification...")
    try:
        classified = SignalProcessor.process_all_signals()
        logger.success(f"Classified {classified} signals.")
    except Exception as e:
        logger.error(f"Signal classification failed: {e}")

    # 7. Extract structured entities (Todos, Financial, FYI events)
    logger.info("Extracting structured entities...")
    try:
        todos = SignalProcessor.extract_todos()
        logger.success(f"Extracted {todos} Todos.")
    except Exception as e:
        logger.error(f"Todo extraction failed: {e}")

    try:
        financials = SignalProcessor.extract_financial_events()
        logger.success(f"Extracted {financials} Financial Events.")
    except Exception as e:
        logger.error(f"Financial event extraction failed: {e}")

    try:
        fyis = SignalProcessor.extract_fyi_events()
        logger.success(f"Extracted {fyis} FYI Events.")
    except Exception as e:
        logger.error(f"FYI event extraction failed: {e}")

    # 8. Run local Financial Outflow Analysis
    logger.info("Running local Financial Outflow Analysis...")
    try:
        FinancialIntelligenceService.run_pipeline()
        logger.success("Local Financial Outflow Analysis completed.")
    except Exception as e:
        logger.error(f"Local Financial Outflow Analysis failed: {e}")

    # 9. Run cloud/Supabase Financial Aggregator
    logger.info("Running cloud/Supabase Financial Aggregation...")
    try:
        FinancialAggregator.run_aggregation()
        logger.success("Cloud Financial Aggregation completed.")
    except Exception as e:
        logger.error(f"Cloud Financial Aggregation failed: {e}")

    # 10. Generate and sync daily briefs for all unique dates represented in the processed signals
    logger.info("Regenerating and syncing Daily Briefs...")
    db = SessionLocal()
    try:
        signals = db.query(Signal).all()
        unique_dates = set()
        for sig in signals:
            if sig.created_at:
                unique_dates.add(sig.created_at.strftime("%Y-%m-%d"))
        
        logger.info(f"Unique dates detected from processed signals: {unique_dates}")
        for date_str in sorted(list(unique_dates)):
            logger.info(f"Generating daily brief for date: {date_str}...")
            DailyBriefGenerator.generate_brief_for_date(date_str)
        logger.success("All Daily Briefs successfully regenerated and synced.")
    except Exception as e:
        logger.error(f"Failed to generate Daily Briefs: {e}")
    finally:
        db.close()

    logger.success("=== REPROCESSING PIPELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
