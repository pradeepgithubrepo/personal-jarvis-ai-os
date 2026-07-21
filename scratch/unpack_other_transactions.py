import os
import sys
from dotenv import load_dotenv
from supabase import create_client, ClientOptions
from collections import defaultdict

sys.path.insert(0, os.getcwd())
from src.agents.financial_summary.aggregator import map_category

def main():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key, options=ClientOptions(schema="jarvis_insights_schemav1"))

    print("Fetching all transactions from financial_transactions...")
    res = client.table("financial_transactions").select("*").execute()
    all_txs = res.data or []
    print(f"Total transactions loaded: {len(all_txs)}")

    # Filter for July 2026 expenses under 'Other' category
    other_txs = []
    for tx in all_txs:
        date_str = tx.get("event_date") or ""
        if date_str.startswith("2026-07") and tx.get("direction") == "DEBIT" and tx.get("transaction_type") != "TRANSFER":
            cat = map_category(tx.get("category"))
            if cat == "Other":
                other_txs.append(tx)

    print(f"Total 'Other' transactions in 2026-07: {len(other_txs)}")
    other_txs.sort(key=lambda x: float(x["amount"]), reverse=True)

    # Grouping
    original_categories = defaultdict(float)
    merchants = defaultdict(float)
    sources = defaultdict(float)

    for tx in other_txs:
        amt = float(tx["amount"])
        original_categories[tx.get("category")] += amt
        merchants[tx.get("merchant") or "Unknown"] += amt
        sources[tx.get("import_source")] += amt

    print("\n--- Breakdown by Original Database Category ---")
    for cat, amt in sorted(original_categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat or 'None'}: \u20b9{amt:,.2f}")

    print("\n--- Breakdown by Import Source File ---")
    for src, amt in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src or 'None'}: \u20b9{amt:,.2f}")

    print("\n--- Top 20 Merchants in 'Other' ---")
    for merch, amt in sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {merch}: \u20b9{amt:,.2f}")

    print("\n--- Detailed Top 20 Transactions in 'Other' ---")
    for idx, tx in enumerate(other_txs[:20]):
        print(f"{idx+1}. Date: {tx['event_date']} | Amt: \u20b9{tx['amount']:,.2f} | Merchant: {tx.get('merchant')} | Orig Cat: {tx.get('category')} | Source File: {tx.get('import_source')} | Narration: {tx.get('raw_narration')[:80]}")

if __name__ == "__main__":
    main()
