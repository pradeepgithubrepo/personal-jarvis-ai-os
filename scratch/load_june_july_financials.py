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
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables missing.")
        sys.exit(1)

    print("Initializing Supabase Client...")
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    print("Fetching understood signals timestamps in batch...")
    us_res = (
        client.table("understood_signals")
        .select("id, qualified_signals(timestamp)")
        .execute()
    )
    ts_map = {}
    for us in us_res.data or []:
        qs = us.get("qualified_signals") or {}
        ts_map[us["id"]] = qs.get("timestamp")

    print("Fetching pending routes for financial_agent...")
    routes_res = (
        client.table("signal_routes")
        .select("id, understood_signal_id, route_reason, route_confidence")
        .eq("agent_name", "financial_agent")
        .eq("route_status", "PENDING")
        .execute()
    )
    pending_routes = routes_res.data or []
    print(f"Total pending routes: {len(pending_routes)}")

    target_routes = []
    print("Filtering routes for June & July 2026...")
    for route in pending_routes:
        us_id = route["understood_signal_id"]
        ts = ts_map.get(us_id)
        if ts and (ts.startswith("2026-06") or ts.startswith("2026-07")):
            target_routes.append(route)

    print(f"Filtered down to {len(target_routes)} routes for June & July 2026.")

    if not target_routes:
        print("No June/July routes found to process.")
        return

    print("Initializing Financial Agent with Mistral as primary LLM...")
    agent = FinancialAgent(provider="mistral")

    print("Running pull ingestion worker on June & July routes...")
    try:
        agent.process_pending_routes(client, target_routes)
        print("June/July ingestion complete!")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
