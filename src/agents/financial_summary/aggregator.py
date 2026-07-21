from decimal import Decimal
from typing import List, Dict, Any, Tuple
from loguru import logger

ALLOWED_CATEGORIES = {
    "Food", "Groceries", "Transport", "Shopping", "Education", "Medical", 
    "Insurance", "Utilities", "Travel", "Investment", "Housing", "Family", "Other"
}

def map_category(raw_category: str | None) -> str:
    """Map any raw category to one of the 13 allowed categories."""
    if not raw_category:
        return "Other"
    
    cat = raw_category.strip().capitalize()
    if cat in ALLOWED_CATEGORIES:
        return cat
        
    # Custom DB category mapping rules
    mapping = {
        "Dining": "Food",
        "Health": "Medical",
        "Fuel": "Transport",
        "Banking": "Other",
        "Entertainment": "Other",
    }
    return mapping.get(cat, "Other")

def aggregate_transactions(transactions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process all transactions and return lists of dicts ready to insert into:
    1. monthly_spending_summary
    2. monthly_category_spend
    3. monthly_merchant_spend
    4. monthly_income_sources
    5. monthly_top_transactions
    """
    # Group transactions by month (YYYY-MM)
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for tx in transactions:
        date_str = tx.get("event_date") or ""
        if len(date_str) >= 7 and date_str[4] == "-" and date_str[0:4].isdigit() and date_str[5:7].isdigit():
            month = date_str[:7]
            by_month.setdefault(month, []).append(tx)
        else:
            logger.warning(f"aggregator: Skipping transaction {tx.get('transaction_id')} with invalid/missing event_date: {date_str}")

    summaries = []
    category_spends = []
    merchant_spends = []
    income_sources = []
    top_transactions = []

    for month, tx_list in sorted(by_month.items()):
        logger.info(f"aggregator: Processing aggregates for month {month} ({len(tx_list)} transactions)...")
        
        month_income = Decimal("0.00")
        month_expense = Decimal("0.00")
        month_transfers = Decimal("0.00")
        tx_count = len(tx_list)

        # Temporary groupings for the month
        cat_group: Dict[str, Dict[str, Any]] = {}
        merchant_group: Dict[str, Dict[str, Any]] = {}
        income_group: Dict[str, Dict[str, Any]] = {}
        expenses_for_ranking = []

        for tx in tx_list:
            amount_dec = Decimal(str(tx["amount"]))
            tx_type = tx.get("transaction_type")
            direction = tx.get("direction")
            is_self = tx.get("is_self_transfer")

            # Resolve transfers vs income vs expense
            if tx_type == "TRANSFER" or is_self is True:
                if direction == "DEBIT":
                    month_transfers += amount_dec
            else:
                if direction == "CREDIT":
                    month_income += amount_dec
                    
                    # Accumulate Income Source
                    source_name = (tx.get("merchant") or tx.get("counterparty") or "Other").strip()
                    if not source_name:
                        source_name = "Other"
                    income_group.setdefault(source_name, {"amount": Decimal("0.00"), "count": 0})
                    income_group[source_name]["amount"] += amount_dec
                    income_group[source_name]["count"] += 1

                elif direction == "DEBIT":
                    month_expense += amount_dec
                    
                    # Map Category Spend
                    mapped_cat = map_category(tx.get("category"))
                    cat_group.setdefault(mapped_cat, {"amount": Decimal("0.00"), "count": 0})
                    cat_group[mapped_cat]["amount"] += amount_dec
                    cat_group[mapped_cat]["count"] += 1

                    # Accumulate Merchant Spend
                    merchant_name = (tx.get("merchant") or tx.get("counterparty") or "Other").strip()
                    if not merchant_name:
                        merchant_name = "Other"
                    merchant_group.setdefault(merchant_name, {"amount": Decimal("0.00"), "count": 0})
                    merchant_group[merchant_name]["amount"] += amount_dec
                    merchant_group[merchant_name]["count"] += 1

                    # Add to candidates for top transactions ranking
                    expenses_for_ranking.append(tx)

        # ─── RECONCILIATION & VALIDATION CHECKS ───
        
        # Rule 1: Sum(Category Spend) = Total Expense
        sum_category = sum(v["amount"] for v in cat_group.values())
        if sum_category != month_expense:
            raise ValueError(
                f"Reconciliation Failed for {month} (Rule 1): "
                f"Sum(Category Spend) = {sum_category} != Total Expense = {month_expense}"
            )

        # Rule 2: Sum(Merchant Spend) = Total Expense
        sum_merchant = sum(v["amount"] for v in merchant_group.values())
        if sum_merchant != month_expense:
            raise ValueError(
                f"Reconciliation Failed for {month} (Rule 2): "
                f"Sum(Merchant Spend) = {sum_merchant} != Total Expense = {month_expense}"
            )

        # Rule 3: Income - Expense = Net Cashflow
        net_cashflow = month_income - month_expense

        logger.info(
            f"aggregator: {month} reconciled successfully. "
            f"Income={month_income} | Expense={month_expense} | Transfers={month_transfers} | Net={net_cashflow}"
        )

        # Add to output datasets (converting Decimals back to floats for database ingestion)
        summaries.append({
            "month_key": month,
            "total_income": float(month_income),
            "total_expense": float(month_expense),
            "total_transfers": float(month_transfers),
            "net_cashflow": float(net_cashflow),
            "transaction_count": tx_count
        })

        for cat, vals in cat_group.items():
            category_spends.append({
                "month_key": month,
                "category": cat,
                "amount": float(vals["amount"]),
                "transaction_count": vals["count"]
            })

        for merch, vals in merchant_group.items():
            merchant_spends.append({
                "month_key": month,
                "merchant_name": merch,
                "amount": float(vals["amount"]),
                "transaction_count": vals["count"]
            })

        for src, vals in income_group.items():
            income_sources.append({
                "month_key": month,
                "source_name": src,
                "amount": float(vals["amount"]),
                "transaction_count": vals["count"]
            })

        # Sort and rank top 10 expenses
        expenses_for_ranking.sort(key=lambda x: Decimal(str(x["amount"])), reverse=True)
        for i, tx in enumerate(expenses_for_ranking[:10]):
            top_transactions.append({
                "month_key": month,
                "transaction_id": tx["transaction_id"],
                "amount": float(tx["amount"]),
                "merchant": tx.get("merchant") or tx.get("counterparty") or "Other",
                "category": map_category(tx.get("category")),
                "rank": i + 1
            })

    return summaries, category_spends, merchant_spends, income_sources, top_transactions
