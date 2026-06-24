# scripts/post_process_current.py
import os
import sys
import time
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.system_initializer import initialize_system
from services.signal_processor import SignalProcessor
from services.financial_aggregator import FinancialAggregator

def main():
    start_time = time.time()
    logger.info("Initializing system runtime context for post-processing...")
    initialize_system()

    logger.info("Step 1: Running signal categories classification...")
    try:
        classified = SignalProcessor.process_all_signals()
        logger.info(f"Classified {classified} signals.")
    except Exception as e:
        logger.exception(f"Classification failed: {e}")

    logger.info("Step 2: Running TODO extraction pipeline...")
    try:
        todos = SignalProcessor.extract_todos()
        logger.info(f"Extracted {todos} TODOs.")
    except Exception as e:
        logger.exception(f"TODO extraction failed: {e}")

    logger.info("Step 3: Running Financial Event extraction pipeline...")
    try:
        financials = SignalProcessor.extract_financial_events()
        logger.info(f"Extracted {financials} Financial Events.")
    except Exception as e:
        logger.exception(f"Financial Event extraction failed: {e}")

    logger.info("Step 4: Running FYI Event extraction pipeline...")
    try:
        fyis = SignalProcessor.extract_fyi_events()
        logger.info(f"Extracted {fyis} FYI Events.")
    except Exception as e:
        logger.exception(f"FYI Event extraction failed: {e}")

    logger.info("Step 5: Running Financial Aggregator spending rollups...")
    try:
        FinancialAggregator.run_aggregation()
        logger.success("Financial Aggregator aggregation complete.")
    except Exception as e:
        logger.exception(f"Financial Aggregator failed: {e}")

    elapsed = time.time() - start_time
    logger.info(f"Post-processing completed in {elapsed:.1f} seconds.")

if __name__ == "__main__":
    main()
