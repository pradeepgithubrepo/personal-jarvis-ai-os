# scratch/analyze_db_quality.py
import sys
from loguru import logger
from services.supabase_repo import SupabaseRepo, supabase

def analyze():
    print("====================================================")
    print("             SUPABASE INGESTION QUALITY ANALYSIS     ")
    print("====================================================")
    
    # 1. Row counts
    tables = [
        "signals",
        "todos",
        "financial_events",
        "fyi_events",
        "monthly_spending_summary",
        "monthly_category_spend",
        "financial_transaction_classification"
    ]
    
    counts = {}
    for table in tables:
        try:
            res = supabase.table(table).select("count", count="exact").limit(1).execute()
            counts[table] = res.count if res.count is not None else len(res.data)
        except Exception as e:
            counts[table] = f"Error: {e}"
            
    for table, count in counts.items():
        print(f"Table '{table}': {count} rows")
        
    print("\n====================================================")
    print("             SAMPLE DATA & QUALITY CHECKS            ")
    print("====================================================")
    
    # 2. Sample Todos
    print("\n--- SAMPLE TODOS ---")
    try:
        todos = supabase.table("todos").select("title, description, priority, status").limit(5).execute().data or []
        if todos:
            for idx, item in enumerate(todos, 1):
                print(f"{idx}. Title: {item.get('title')}\n   Desc: {item.get('description')}\n   Priority: {item.get('priority')} | Status: {item.get('status')}\n")
        else:
            print("No todos found.")
    except Exception as e:
        print(f"Error fetching todos: {e}")

    # 3. Sample Financial Events
    print("\n--- SAMPLE FINANCIAL EVENTS ---")
    try:
        events = supabase.table("financial_events").select("merchant, amount, category, status, event_timestamp").limit(8).execute().data or []
        if events:
            for idx, item in enumerate(events, 1):
                print(f"{idx}. Merchant: {item.get('merchant')} | Amount: {item.get('amount')} | Category: {item.get('category')} | Status: {item.get('status')} | Date: {item.get('event_timestamp')}")
        else:
            print("No financial events found.")
    except Exception as e:
        print(f"Error fetching financial events: {e}")

    # 4. Sample FYI Events
    print("\n--- SAMPLE FYI EVENTS ---")
    try:
        fyis = supabase.table("fyi_events").select("title, summary, category").limit(5).execute().data or []
        if fyis:
            for idx, item in enumerate(fyis, 1):
                print(f"{idx}. Title: {item.get('title')}\n   Summary: {item.get('summary')}\n   Category: {item.get('category')}\n")
        else:
            print("No FYI events found.")
    except Exception as e:
        print(f"Error fetching FYI events: {e}")

    # 5. Monthly Spending Summaries
    print("\n--- MONTHLY SPENDING SUMMARY ---")
    try:
        summaries = supabase.table("monthly_spending_summary").select("month_key, total_spend, transaction_count").order("month_key").execute().data or []
        if summaries:
            for item in summaries:
                print(f"Month: {item.get('month_key')} | Total Spend: {item.get('total_spend')} | Transactions: {item.get('transaction_count')}")
        else:
            print("No monthly summaries found.")
    except Exception as e:
        print(f"Error fetching monthly summaries: {e}")

    # 6. Monthly Category Spends
    print("\n--- MONTHLY CATEGORY SPENDS ---")
    try:
        cat_spends = supabase.table("monthly_category_spend").select("month_key, category_name, amount, transaction_count").order("month_key").order("amount", desc=True).execute().data or []
        if cat_spends:
            current_month = None
            for item in cat_spends:
                m_key = item.get('month_key')
                if m_key != current_month:
                    current_month = m_key
                    print(f"\nMonth: {current_month}")
                print(f"  - {item.get('category_name')}: {item.get('amount')} ({item.get('transaction_count')} txs)")
        else:
            print("No category spending data found.")
    except Exception as e:
        print(f"Error fetching category spends: {e}")

if __name__ == "__main__":
    analyze()
