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
from services.daily_brief_generator import DailyBriefGenerator


def run_brief_generator():
    logger.info("Initializing database...")
    initialize_database()

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info(f"Generating Daily Brief for today ({today_str})...")
    
    brief_data = DailyBriefGenerator.generate_brief_for_date(today_str)
    
    # Beautiful presentation of the daily brief
    print("\n" + "="*70)
    print(f"             DAILY INTELLIGENCE BRIEF - {today_str}")
    print("="*70)

    # 1. IMPORTANT ITEMS
    print("\n🚨 IMPORTANT ITEMS:")
    if not brief_data.get("important_items"):
        print("  - None")
    else:
        for item in brief_data["important_items"]:
            itype = item["type"].upper().replace("_", " ")
            details = ""
            if "amount" in item and item["amount"]:
                details += f" (Amount: {item['amount']} {item.get('currency')})"
            if "due_date" in item and item["due_date"]:
                details += f" [Due: {item['due_date']}]"
            print(f"  • [{itype}] {item['title']}{details}")

    # 2. TODOS
    print("\n📋 ACTIONS / TODOS:")
    if not brief_data.get("todos"):
        print("  - None")
    else:
        for t in brief_data["todos"]:
            print(f"  • [{t['priority'].upper()}] {t['title']} (Due: {t['due_date']})")

    # 3. FINANCIAL SUMMARY
    print("\n💳 FINANCIAL SUMMARY:")
    fin = brief_data.get("financial", {})
    print(f"  • Total Credit: {fin.get('total_credit'):,.2f} INR")
    print(f"  • Total Debit : {fin.get('total_debit'):,.2f} INR")
    print("\n  Transactions today:")
    if not fin.get("events"):
        print("    - None")
    else:
        for e in fin["events"]:
            print(f"    • [{e['type'].upper()}] {e['title'][:80]}... (Amount: {e['amount']} {e['currency']})")

    # 4. FYI NOTIFICATIONS
    print("\nℹ️ FYI NOTIFICATIONS:")
    if not brief_data.get("fyi"):
        print("  - None")
    else:
        for f in brief_data["fyi"]:
            print(f"  • [{f['fyi_type'].upper()}] {f['title'][:90]}...")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    run_brief_generator()
