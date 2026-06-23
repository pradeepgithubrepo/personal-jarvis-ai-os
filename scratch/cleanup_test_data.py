# scratch/cleanup_test_data.py

import os
import sys
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.supabase_repo import supabase, SupabaseRepo
from services.financial_aggregator import FinancialAggregator

def cleanup():
    logger.info("Starting cleanup of test-polluted data from Supabase...")

    # 1. Fetch all signals to identify test ones
    signals = supabase.table("signals").select("signal_id, message").execute().data or []
    test_signal_ids = []
    for s in signals:
        msg = (s.get("message") or "").lower()
        if "test" in msg:
            test_signal_ids.append(s["signal_id"])

    logger.info(f"Found {len(test_signal_ids)} test signals in Supabase.")

    if test_signal_ids:
        # Delete related financial events
        res_events = supabase.table("financial_events").delete().in_("source_signal_id", test_signal_ids).execute()
        logger.info(f"Deleted related financial events from Supabase.")

        # Delete related fyi events
        res_fyi = supabase.table("fyi_events").delete().in_("source_signal_id", test_signal_ids).execute()
        logger.info(f"Deleted related fyi events from Supabase.")

        # Delete related todos
        res_todos = supabase.table("todos").delete().in_("source_signal_id", test_signal_ids).execute()
        logger.info(f"Deleted related todos from Supabase.")

        # Delete the signals themselves
        res_sig = supabase.table("signals").delete().in_("signal_id", test_signal_ids).execute()
        logger.info(f"Deleted test signals from Supabase.")

    # 2. Rerun financial aggregation on the clean data
    logger.info("Rerunning financial aggregator on clean data...")
    FinancialAggregator.run_aggregation()
    logger.success("Cleanup and re-aggregation completed successfully!")

if __name__ == "__main__":
    cleanup()
