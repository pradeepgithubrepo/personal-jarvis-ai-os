import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher
from src.agents.todo.todo_agent import TodoAgent

def main():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)
    
    target_ids = ["14945a87-b914-4aaa-976b-6d70c615caed", "5f52fe11-2d1b-4fb5-9c43-5a5c1ab1d953"]
    
    for qid in target_ids:
        print(f"\nProcessing qualified ID: {qid}")
        
        # 1. Fetch the understood_signals record for this qualified_signal_id
        res = client.table("understood_signals").select("*").eq("qualified_signal_id", qid).execute()
        if not res.data:
            print(f"No understood_signals record found for qualified_signal_id {qid}.")
            continue
            
        us_row = res.data[0]
        us_id = us_row["id"]
        
        # Fetch qualified message
        res_qs = client.table("qualified_signals").select("message").eq("id", qid).execute()
        message = res_qs.data[0]["message"] if res_qs.data else ""
        
        # 2. Determine updated contract details
        contract = us_row.get("contract_json") or {}
        if not isinstance(contract, dict):
            contract = {}
            
        if qid == "14945a87-b914-4aaa-976b-6d70c615caed":
            contract["task_name"] = "Pay flat maintenance charges for June 2026"
            contract["assignee"] = "user"
            contract["due_date"] = "Jun26"
        else:
            contract["task_name"] = "Complete school homework: Book 1 pg 9"
            contract["assignee"] = "parent"
            contract["due_date"] = None
            
        contract["requires_action"] = True
        contract["fyi_candidate"] = False
        contract["noise_candidate"] = False
        contract["memory_candidate"] = True
        contract["financial_candidate"] = False
        
        # 3. Update understood_signals table in Supabase
        update_data = {
            "signal_type": "ACTION",
            "reason": "Manual override: Homework/Maintenance correction",
            "contract_json": contract
        }
        
        client.table("understood_signals").update(update_data).eq("id", us_id).execute()
        print(f"Updated understood_signals record {us_id} to ACTION.")
        
        # 4. Fetch the updated row to pass to router
        res_updated = client.table("understood_signals").select("*").eq("id", us_id).execute()
        updated_us_row = res_updated.data[0]
        
        # 5. Clear existing signal_routes for this understood_signal_id
        res_del = client.table("signal_routes").delete().eq("understood_signal_id", us_id).execute()
        print(f"Cleared {len(res_del.data) if res_del.data else 0} old signal_routes.")
        
        # 6. Route and Dispatch the updated signal
        router = SignalRouter()
        dispatcher = ContractDispatcher()
        
        route_decision = router.route(updated_us_row)
        print(f"Routing decision: {route_decision}")
        
        dispatcher.dispatch(route_decision, client)
        print("Dispatched to signal_routes.")
        
    # 7. Run TodoAgent to process pending routes
    print("\nRunning TodoAgent to ingest the new tasks...")
    todo_agent = TodoAgent()
    todo_agent.process_pending_routes(client)
    print("Done!")

if __name__ == "__main__":
    main()
