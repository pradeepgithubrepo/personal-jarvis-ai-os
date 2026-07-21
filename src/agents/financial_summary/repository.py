from typing import Any, List, Dict
from loguru import logger

def fetch_all_transactions(supabase_client: Any) -> List[Dict[str, Any]]:
    """Fetch all rows from the financial_transactions table."""
    logger.info("repository: Fetching all rows from financial_transactions...")
    res = (
        supabase_client
        .table("financial_transactions")
        .select("*")
        .execute()
    )
    data = res.data or []
    logger.info(f"repository: Loaded {len(data)} transactions.")
    return data

def upsert_spending_summaries(supabase_client: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    logger.info(f"repository: Upserting {len(rows)} rows into monthly_spending_summary...")
    supabase_client.table("monthly_spending_summary").upsert(rows).execute()

def upsert_category_spends(supabase_client: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    logger.info(f"repository: Upserting {len(rows)} rows into monthly_category_spend...")
    supabase_client.table("monthly_category_spend").upsert(rows).execute()

def upsert_merchant_spends(supabase_client: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    logger.info(f"repository: Upserting {len(rows)} rows into monthly_merchant_spend...")
    supabase_client.table("monthly_merchant_spend").upsert(rows).execute()

def upsert_income_sources(supabase_client: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    logger.info(f"repository: Upserting {len(rows)} rows into monthly_income_sources...")
    supabase_client.table("monthly_income_sources").upsert(rows).execute()

def upsert_top_transactions(supabase_client: Any, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    logger.info(f"repository: Upserting {len(rows)} rows into monthly_top_transactions...")
    # First delete any existing top transactions for the months being updated to avoid ranking orphans,
    # or rely on upsert (rank is the primary key, so upsert for same month_key + rank works perfectly!)
    supabase_client.table("monthly_top_transactions").upsert(rows).execute()
