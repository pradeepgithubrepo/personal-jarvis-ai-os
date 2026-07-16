import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.todo.todo_agent import TodoAgent

def main():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)
    
    print("Running TodoAgent pull worker to process pending routes...")
    todo_agent = TodoAgent()
    todo_agent.process_pending_routes(client)
    print("TodoAgent work complete.")

    # Show count of tasks created
    res_tasks = client.table("tasks").select("id, title, status, priority, due_datetime").execute()
    print(f"\nTotal tasks created: {len(res_tasks.data)}")
    for t in res_tasks.data:
        print(f"  - [{t.get('priority')}] {t.get('title')} (Due: {t.get('due_datetime')})")

if __name__ == "__main__":
    main()
