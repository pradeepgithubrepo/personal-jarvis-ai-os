# scripts/run_full_pipeline.py

import os
import sys
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.system_initializer import initialize_system
from consumer.consumer_service import ConsumerService
from services.mobile_signal_pipeline import MobileSignalPipeline
from services.email_pipeline import EmailPipeline
from services.signal_processor import SignalProcessor
from services.daily_brief_generator import DailyBriefGenerator


def run_pipeline():
    logger.info("==================================================")
    logger.info("STARTING JARVIS FULL SYNCHRONIZATION PIPELINE")
    logger.info("==================================================")

    # 1. System initialization
    try:
        logger.info("Initializing system and loading context...")
        initialize_system()
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        sys.exit(1)

    # 2. Sync mobile signals from Supabase Storage bucket
    try:
        logger.info("Syncing mobile signals from Supabase Storage...")
        ConsumerService().run_sync()
    except Exception as e:
        logger.error(f"Consumer service sync failed: {e}")

    # 3. LLM Mobile Signal Processing Pipeline
    try:
        logger.info("Running Mobile Signal Pipeline (LLM)...")
        MobileSignalPipeline().run()
    except Exception as e:
        logger.error(f"Mobile signal pipeline run failed: {e}")

    # 4. LLM Email Processing Pipeline
    try:
        logger.info("Running Email Ingestion & Processing Pipeline...")
        EmailPipeline().run()
    except Exception as e:
        logger.error(f"Email pipeline run failed: {e}")

    # 5. Classify all unclassified signals
    try:
        logger.info("Classifying all unclassified signals...")
        processed_signals = SignalProcessor.process_all_signals()
        logger.info(f"Classified {processed_signals} signals.")
    except Exception as e:
        logger.error(f"Signal classification failed: {e}")

    # 6. Extract structured entities (TODOs, Financials, FYIs)
    try:
        logger.info("Extracting TODOs...")
        todos_count = SignalProcessor.extract_todos()
        logger.info(f"Extracted {todos_count} TODOs.")
    except Exception as e:
        logger.error(f"TODO extraction failed: {e}")

    try:
        logger.info("Extracting Financial Events...")
        financial_count = SignalProcessor.extract_financial_events()
        logger.info(f"Extracted {financial_count} Financial Events.")
    except Exception as e:
        logger.error(f"Financial event extraction failed: {e}")

    try:
        logger.info("Extracting FYI Events...")
        fyi_count = SignalProcessor.extract_fyi_events()
        logger.info(f"Extracted {fyi_count} FYI Events.")
    except Exception as e:
        logger.error(f"FYI event extraction failed: {e}")

    # Run financial intelligence outflow analysis
    try:
        from services.financial_intelligence import FinancialIntelligenceService
        logger.info("Running Financial Outflow Analysis Pipeline...")
        FinancialIntelligenceService.run_pipeline()
    except Exception as e:
        logger.error(f"Financial Outflow Analysis Pipeline failed: {e}")

    # 7. Generate Daily Brief and Sync back to Supabase
    try:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        logger.info(f"Generating Daily Brief for date: {today_str}...")
        DailyBriefGenerator.generate_brief_for_date(today_str)
        logger.success("Daily Brief generated and synchronized to Supabase successfully!")
    except Exception as e:
        logger.error(f"Failed to generate or sync Daily Brief: {e}")

    logger.info("==================================================")
    logger.info("JARVIS PIPELINE EXECUTION COMPLETE")
    logger.info("==================================================")


if __name__ == "__main__":
    run_pipeline()
