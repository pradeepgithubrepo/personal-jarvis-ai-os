import os
import sys
import json
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from loguru import logger

# Insert workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher

def main():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)
    
    # 1. Clear signal_routes
    print("Clearing signal_routes...")
    client.table("signal_routes").delete().neq("id", str(uuid.uuid4())).execute()
    
    # 2. Fetch understood signals
    print("Fetching understood signals...")
    res = client.table("understood_signals").select("*").execute()
    signals = res.data
    print(f"Loaded {len(signals)} understood signals.")
    
    # 3. Initialize routing & dispatch
    router = SignalRouter()
    dispatcher = ContractDispatcher()
    
    print("Routing and dispatching signals...")
    success_count = 0
    fail_count = 0
    
    for us in signals:
        try:
            route_decision = router.route(us)
            dispatch_result = dispatcher.dispatch(route_decision, client)
            success_count += 1
        except Exception as e:
            print(f"Failed to route/dispatch signal {us.get('id')}: {e}")
            fail_count += 1
            
    print(f"Completed! Success: {success_count}, Fails: {fail_count}")

if __name__ == "__main__":
    main()
