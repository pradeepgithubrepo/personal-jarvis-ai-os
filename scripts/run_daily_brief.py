# scripts/run_daily_brief.py

import os
import sys
import json
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.daily_brief import DailyBrief
from services.daily_brief_agent import DailyBriefAgent


def run_brief_generator():
    logger.info("Initializing database...")
    initialize_database()

    db = SessionLocal()
    try:
        logger.info("Generating Morning and Evening Briefs using DailyBriefAgent...")
        brief_ids = DailyBriefAgent.generate_briefs(db)
        
        morning_brief = db.get(DailyBrief, brief_ids["morning_brief_id"])
        evening_brief = db.get(DailyBrief, brief_ids["evening_brief_id"])

        print("\n" + "="*70)
        print("             DAILY INTELLIGENCE BRIEF (MORNING)")
        print("="*70)
        if morning_brief:
            print(morning_brief.content)
        else:
            print("Failed to load morning brief.")
        print("="*70 + "\n")

        print("\n" + "="*70)
        print("             DAILY INTELLIGENCE BRIEF (EVENING)")
        print("="*70)
        if evening_brief:
            print(evening_brief.content)
        else:
            print("Failed to load evening brief.")
        print("="*70 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_brief_generator()
