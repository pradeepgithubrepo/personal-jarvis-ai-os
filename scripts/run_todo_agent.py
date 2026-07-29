"""
scripts/run_todo_agent.py

CLI script to run the To-Do Agent worker on the laptop backend.
Queries PENDING route entries for todo_agent in Supabase, reasons over them,
and ingests/merges tasks.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Insert workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.todo.todo_agent import TodoAgent

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
    
    print("Initializing To-Do Agent...")
    # Leveraging priority hierarchy (Gemini -> Cerebras -> Local)
    agent = TodoAgent()
    
    print("Running pull ingestion worker for PENDING route pointers...")
    try:
        agent.process_pending_routes(client)
        print("To-Do Agent pull ingestion complete!")
    except Exception as e:
        print(f"Error during To-Do Agent execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
