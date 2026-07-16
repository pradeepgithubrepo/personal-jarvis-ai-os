"""
scripts/run_fyi_agent.py

CLI script to run the FYI Agent worker on the backend.
Queries PENDING route entries for fyi_agent in Supabase, classifies them
into structured/rule-based/LLM paths, and inserts information items.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Insert workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.fyi.fyi_agent import FyiAgent


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
    
    print("Initializing FYI Agent...")
    # Leveraging priority hierarchy (Gemini -> Cerebras -> Local)
    agent = FyiAgent()
    
    print("Running pull ingestion worker for PENDING FYI route pointers...")
    try:
        agent.process_pending_routes(client)
        print("FYI Agent pull ingestion complete!")
    except Exception as e:
        print(f"Error during FYI Agent execution: {e}")
        sys.exit(1)
        
    print("Running database retention policy pruner...")
    try:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        
        e_cutoff = (now - timedelta(days=7)).isoformat()
        l_cutoff = (now - timedelta(days=30)).isoformat()
        m_cutoff = (now - timedelta(days=180)).isoformat()
        
        res_e = client.table("information_items").delete().eq("importance_level", "EPHEMERAL").lt("created_at", e_cutoff).execute()
        res_l = client.table("information_items").delete().eq("importance_level", "LOW").lt("created_at", l_cutoff).execute()
        res_m = client.table("information_items").delete().eq("importance_level", "MEDIUM").lt("created_at", m_cutoff).execute()
        
        pruned_count = len(res_e.data or []) + len(res_l.data or []) + len(res_m.data or [])
        print(f"Retention pruner complete. Removed {pruned_count} expired records.")
    except Exception as e:
        print(f"Warning: Database pruning failed: {e}")


if __name__ == "__main__":
    main()
