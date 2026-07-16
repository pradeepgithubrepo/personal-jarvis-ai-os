import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from collections import Counter

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher

def main():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)
    
    # 1. Clear signal_routes
    print("Clearing signal_routes table...")
    res_del = client.table("signal_routes").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print(f"Cleared signal_routes completed. Removed records: {len(res_del.data) if res_del.data else 0}")
    
    # 2. Fetch all understood signals
    print("Fetching understood_signals...")
    res_us = client.table("understood_signals").select("*").execute()
    understood_signals = res_us.data
    print(f"Loaded {len(understood_signals)} understood signals.")
    
    # 3. Route and dispatch
    print("Routing and dispatching to signal_routes...")
    router = SignalRouter()
    dispatcher = ContractDispatcher()
    
    for idx, us in enumerate(understood_signals):
        route_decision = router.route(us)
        dispatcher.dispatch(route_decision, client)
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(understood_signals)}...")
            
    print("Routing complete.")
    
    # 4. Fetch loaded signal_routes count and details
    res_sr_all = client.table("signal_routes").select("*").execute()
    signal_routes = res_sr_all.data
    print(f"Total signal_routes rows created: {len(signal_routes)}")
    
    # Distribution of routes by target agent
    agent_counts = Counter(r.get("agent_name") for r in signal_routes)
    print("\nRoute Distribution by Agent:")
    for agent, count in agent_counts.items():
        print(f"  {agent}: {count}")
        
    # Status distribution
    status_counts = Counter(r.get("route_status") for r in signal_routes)
    print("\nRoute Status Distribution:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
        
    # 5. Run verification audits
    print("\n--- Running Routing Audits ---")
    
    # Audit 1: Lineage Check
    res_sr_lineage = client.table("signal_routes").select("id, understood_signals:understood_signal_id(id)").execute()
    sr_lineage_fails = sum(1 for row in res_sr_lineage.data if not row.get("understood_signals"))
    
    # Audit 2: Reason Check
    res_sr_reason = client.table("signal_routes").select("id, route_reason").execute()
    sr_reason_fails = sum(1 for row in res_sr_reason.data if not row.get("route_reason"))
    
    # Audit 3: Confidence Check
    res_sr_conf = client.table("signal_routes").select("route_confidence, understood_signals:understood_signal_id(confidence)").execute()
    sr_conf_fails = sum(1 for row in res_sr_conf.data if not row.get("understood_signals") or row["route_confidence"] != row["understood_signals"]["confidence"])
    
    print(f"Lineage Check (FK constraints) Fails: {sr_lineage_fails} ({'PASS' if sr_lineage_fails == 0 else 'FAIL'})")
    print(f"Route Reason Check Fails: {sr_reason_fails} ({'PASS' if sr_reason_fails == 0 else 'FAIL'})")
    print(f"Route Confidence Check Fails: {sr_conf_fails} ({'PASS' if sr_conf_fails == 0 else 'FAIL'})")

if __name__ == "__main__":
    main()
