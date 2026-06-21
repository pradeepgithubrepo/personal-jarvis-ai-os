# scripts/run_supabase_sync.py

import os
import sys
import argparse
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database
from services.supabase_sync_service import SupabaseSyncService


def run_sync():
    parser = argparse.ArgumentParser(description="Sync a Daily Brief from local SQLite to Supabase jarvis-insights bucket.")
    parser.add_argument(
        "--date",
        type=str,
        help="Date to sync in YYYY-MM-DD format (defaults to today's UTC date)",
        default=None
    )
    args = parser.parse_args()

    # Determine date
    if args.date:
        date_str = args.date
    else:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info("Initializing database...")
    initialize_database()

    logger.info(f"Triggering manual Supabase sync for date: {date_str}...")
    success = SupabaseSyncService.sync_brief_for_date(date_str)
    
    if success:
        logger.success(f"SUCCESS: Daily brief for {date_str} has been successfully synced to Supabase!")
        sys.exit(0)
    else:
        logger.error(f"FAILURE: Failed to sync daily brief for {date_str} to Supabase. Check log messages above.")
        sys.exit(1)


if __name__ == "__main__":
    run_sync()
