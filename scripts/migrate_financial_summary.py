# scripts/migrate_financial_summary.py

import os
import sys
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_aggregator import FinancialAggregator
from services.supabase_repo import SupabaseRepo, supabase


def run_migration_and_validation():
    logger.info("Initializing Financial Outflow Summary Migration and Backfill...")

    # 1. Trigger Aggregation
    logger.info("Step 1: Running FinancialAggregator on Supabase records...")
    try:
        FinancialAggregator.run_aggregation()
    except Exception as ae:
        logger.error(f"Failed to run aggregator: {ae}")
        sys.exit(1)

    # 2. Validation
    logger.info("Step 2: Commencing data validation...")
    
    events = SupabaseRepo.fetch_financial_events()
    summaries = SupabaseRepo.fetch_monthly_spending_summaries()
    category_spends = SupabaseRepo.fetch_monthly_category_spends()

    if not summaries:
        logger.error("Validation failed: No monthly spending summaries retrieved from Supabase after aggregation.")
        sys.exit(1)

    # Fetch signals to resolve credit/debit transaction types for validation
    try:
        signals_data = supabase.table("signals").select("signal_id, message").execute().data or []
        signal_messages = {s["signal_id"]: s["message"] for s in signals_data}
    except Exception as e:
        logger.error(f"Failed to fetch signals from Supabase: {e}")
        signal_messages = {}

    logger.info(f"Retrieved {len(summaries)} monthly spending summaries from Supabase.")

    # Validate totals against financial_events for each month
    validation_passed = True
    for summary in summaries:
        month_key = summary["month_key"]
        
        # Get transaction list in month boundaries
        start_date = datetime.strptime(month_key, "%Y-%m")
        # Next month minus 1 second
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)

        total_tx_debit = 0.0
        for e in events:
            dt_str = e.get("event_timestamp")
            if dt_str:
                try:
                    dt_clean = dt_str.replace("Z", "").split(".")[0]
                    dt = datetime.fromisoformat(dt_clean)
                except Exception:
                    continue
                
                if start_date <= dt < end_date and e.get("category") != "INTERNAL_TRANSFER":
                    sig_id = e.get("source_signal_id")
                    message = (signal_messages.get(sig_id) or "").lower()
                    
                    is_credit = "credited" in message or "salary" in message or "received" in message or "deposit" in message or "credit alert" in message
                    if not is_credit:
                        total_tx_debit += float(e.get("amount") or 0)

        # Sum of Category Spends for this month
        month_cat_spends = [cs for cs in category_spends if cs["month_key"] == month_key]
        total_cat_debit = sum(float(cs["amount"] or 0) for cs in month_cat_spends)

        # Compare values
        logger.info(f"Month: {month_key}")
        logger.info(f"  - Transaction-Level Total Debits:  {total_tx_debit:,.2f} INR")
        logger.info(f"  - Monthly Summary Total Spend:      {float(summary['total_spend']):,.2f} INR")
        logger.info(f"  - Sum of Category Spend Records:    {total_cat_debit:,.2f} INR")

        # Tolerating floating point representation differences
        diff1 = abs(total_tx_debit - float(summary["total_spend"]))
        diff2 = abs(total_cat_debit - float(summary["total_spend"]))
        
        if diff1 > 0.01 or diff2 > 0.01:
            logger.error(f"  ❌ Totals mismatch for month {month_key}! Mismatch amount: {max(diff1, diff2)}")
            validation_passed = False
        else:
            logger.success(f"  ✅ Validation passed for month {month_key}!")

    if validation_passed:
        logger.success("🎉 ALL MONTHLY SPENDING SUMMARY INTEGRITY VALIDATIONS PASSED SUCCESSFULLY!")
    else:
        logger.error("❌ Integrity validations failed. Check the calculations.")
        sys.exit(1)


if __name__ == "__main__":
    run_migration_and_validation()
