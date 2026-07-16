"""
scripts/run_financial_agent.py

CLI runner for the Financial Agent V1 pull worker.
Reads PENDING signal_routes for financial_agent, runs the full 5-stage
deterministic pipeline, and writes to financial_transactions + transaction_evidence.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_financial_agent.py

Mirrors: scripts/run_todo_agent.py
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.financial.financial_agent import FinancialAgent


def main():
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables missing.")
        sys.exit(1)

    print("Connecting to Supabase...")
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    print("Initializing Financial Agent...")
    agent = FinancialAgent()

    print("Running pull ingestion worker for PENDING financial routes...")
    try:
        agent.process_pending_routes(client)
        print("Financial Agent pull ingestion complete.")
    except Exception as e:
        print(f"ERROR during Financial Agent execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
