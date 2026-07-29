import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from loguru import logger

# Insert project root into python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.financial_summary import repository, aggregator

def generate_validation_report(
    summaries: list,
    category_spends: list,
    merchant_spends: list,
    income_sources: list,
    top_transactions: list
) -> str:
    """Generate the validation markdown report."""
    lines = []
    lines.append("# FINANCIAL_SUMMARY_PHASE1_VALIDATION")
    lines.append("")
    lines.append("This report validates the monthly aggregates produced by Phase 1 of the Financial Summary Agent.")
    lines.append("")
    
    # ── Summary of Months ──
    lines.append("## Months Processed Summary")
    lines.append("")
    lines.append("| Month | Total Income | Total Expense | Total Transfers | Net Cashflow | Transaction Count |")
    lines.append("|---|---|---|---|---|---|")
    for s in summaries:
        lines.append(
            f"| {s['month_key']} | ₹{s['total_income']:,.2f} | ₹{s['total_expense']:,.2f} | "
            f"₹{s['total_transfers']:,.2f} | ₹{s['net_cashflow']:,.2f} | {s['transaction_count']} |"
        )
    lines.append("")

    # ── Top Categories per Month ──
    lines.append("## Top Categories per Month")
    lines.append("")
    # Group category spends by month
    cats_by_month = {}
    for c in category_spends:
        cats_by_month.setdefault(c["month_key"], []).append(c)
    
    for month, c_list in sorted(cats_by_month.items()):
        lines.append(f"### Category Spending - {month}")
        lines.append("")
        lines.append("| Category | Amount | Transaction Count |")
        lines.append("|---|---|---|")
        # Sort descending by amount
        for c in sorted(c_list, key=lambda x: x["amount"], reverse=True):
            lines.append(f"| {c['category']} | ₹{c['amount']:,.2f} | {c['transaction_count']} |")
        lines.append("")

    # ── Top Merchants per Month ──
    lines.append("## Top Merchants per Month")
    lines.append("")
    merchants_by_month = {}
    for m in merchant_spends:
        merchants_by_month.setdefault(m["month_key"], []).append(m)

    for month, m_list in sorted(merchants_by_month.items()):
        lines.append(f"### Top Merchants - {month}")
        lines.append("")
        lines.append("| Merchant | Amount | Transaction Count |")
        lines.append("|---|---|---|")
        # Sort descending, show top 5
        sorted_m = sorted(m_list, key=lambda x: x["amount"], reverse=True)
        for m in sorted_m[:5]:
            lines.append(f"| {m['merchant_name']} | ₹{m['amount']:,.2f} | {m['transaction_count']} |")
        if len(sorted_m) > 5:
            lines.append(f"| *And {len(sorted_m) - 5} other merchants* | | |")
        lines.append("")

    # ── Top Income Sources ──
    lines.append("## Top Income Sources per Month")
    lines.append("")
    incomes_by_month = {}
    for i in income_sources:
        incomes_by_month.setdefault(i["month_key"], []).append(i)

    for month, i_list in sorted(incomes_by_month.items()):
        lines.append(f"### Income Sources - {month}")
        lines.append("")
        lines.append("| Source | Amount | Transaction Count |")
        lines.append("|---|---|---|")
        for i_item in sorted(i_list, key=lambda x: x["amount"], reverse=True):
            lines.append(f"| {i_item['source_name']} | ₹{i_item['amount']:,.2f} | {i_item['transaction_count']} |")
        lines.append("")

    # ── Reconciliation Results ──
    lines.append("## Reconciliation & Validation Results")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> All monthly datasets successfully validated against the ledger assertions:")
    lines.append("> 1. **Rule 1**: Sum of Category Spending matches the Total Expense exactly.")
    lines.append("> 2. **Rule 2**: Sum of Merchant Spending matches the Total Expense exactly.")
    lines.append("> 3. **Rule 3**: Income minus Expense matches the Net Cashflow exactly.")
    lines.append("> 4. **Rule 4**: Transfers are verified to be excluded from spending aggregates.")
    lines.append("")
    lines.append("### Status: **PASSED ✅**")

    return "\n".join(lines)

def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        logger.error("runner: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing.")
        sys.exit(1)

    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(url, key, options=options)

    # 1. Fetch transactions
    tx_list = repository.fetch_all_transactions(client)
    if not tx_list:
        logger.warning("runner: No transactions returned. Aggregation aborted.")
        return

    # 2. Aggregate
    logger.info("runner: Processing transaction aggregation...")
    try:
        summaries, category_spends, merchant_spends, income_sources, top_transactions = (
            aggregator.aggregate_transactions(tx_list)
        )
    except Exception as e:
        logger.exception(f"runner: Aggregation failed validation: {e}")
        sys.exit(1)

    # 3. Upsert back to Supabase
    logger.info("runner: Writing monthly aggregates to Supabase...")
    try:
        repository.upsert_spending_summaries(client, summaries)
        repository.upsert_category_spends(client, category_spends)
        repository.upsert_merchant_spends(client, merchant_spends)
        repository.upsert_income_sources(client, income_sources)
        repository.upsert_top_transactions(client, top_transactions)
        logger.info("runner: All database updates completed successfully.")
    except Exception as e:
        logger.error(f"runner: Failed to write aggregates to DB: {e}")
        sys.exit(1)

    # 4. Generate Validation Report
    logger.info("runner: Generating validation report...")
    report_content = generate_validation_report(
        summaries, category_spends, merchant_spends, income_sources, top_transactions
    )
    
    # Save report to root directory
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "FINANCIAL_SUMMARY_PHASE1_VALIDATION.md"
    )
    with open(report_path, "w") as f:
        f.write(report_content)
        
    logger.info(f"runner: Validation report written to {report_path}")

if __name__ == "__main__":
    main()
