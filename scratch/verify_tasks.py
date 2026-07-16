import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

load_dotenv()
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
opts = ClientOptions(schema="jarvis_insights_schemav1")
client = create_client(url, key, options=opts)

# Check task count
res_count = client.table("tasks").select("id", count="exact").limit(1).execute()
print(f"Total tasks in database: {res_count.count}")

# Fetch recent tasks
res_tasks = client.table("tasks").select("id, title, status, priority").order("created_at", desc=True).limit(10).execute()
print("Recent tasks:")
for r in res_tasks.data:
    print(f"  - Title: {r['title']} | Status: {r['status']} | Priority: {r['priority']}")

# Check pending routes for todo_agent
res_pending = client.table("signal_routes").select("id", count="exact").eq("agent_name", "todo_agent").eq("route_status", "PENDING").limit(1).execute()
print(f"Remaining pending todo routes: {res_pending.count}")
