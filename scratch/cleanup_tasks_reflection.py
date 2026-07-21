import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

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

    print("Fetching all tasks from the tasks table...")
    res = client.table("tasks").select("*").execute()
    initial_tasks = res.data or []
    print(f"Loaded {len(initial_tasks)} tasks.")

    # Sort tasks by created_at ascending (or fallback to id)
    initial_tasks.sort(key=lambda x: x.get("created_at") or x.get("id"))

    agent = TodoAgent()

    updated_count = 0
    merged_count = 0
    error_count = 0
    no_change_count = 0

    deleted_ids = set()

    for task in initial_tasks:
        task_id = task["id"]

        if task_id in deleted_ids:
            continue

        # Fetch current record state in case it was updated by a previous merge
        current_res = client.table("tasks").select("*").eq("id", task_id).execute()
        if not current_res.data:
            deleted_ids.add(task_id)
            continue
        
        current_task = current_res.data[0]

        print(f"\nProcessing Task: {current_task['title']} (ID: {task_id})")
        res_reflect = agent._reflect_on_created_task(client, current_task)
        status = res_reflect.get("status")

        if status == "UPDATED":
            if res_reflect.get("title") != current_task["title"] or res_reflect.get("description") != current_task["description"]:
                updated_count += 1
                print(f" -> Updated/Renamed to: {res_reflect.get('title')}")
            else:
                no_change_count += 1
                print(" -> Checked: OK (No changes needed)")
        elif status == "MERGED":
            merged_count += 1
            deleted_ids.add(task_id)
            print(f" -> Merged and Deleted! Matched task ID: {res_reflect.get('matched_task_id')}")
        elif status == "ERROR":
            error_count += 1
            print(f" -> Error during reflection: {res_reflect.get('error')}")

    # Fetch final task count
    final_res = client.table("tasks").select("*").execute()
    final_tasks = final_res.data or []

    print("\n==================================================")
    print("             TASKS REFLECTION CLEANUP REPORT")
    print("==================================================")
    print(f"Initial tasks: {len(initial_tasks)}")
    print(f"Tasks updated/renamed: {updated_count}")
    print(f"Tasks merged and deleted (duplicates): {merged_count}")
    print(f"Tasks without changes: {no_change_count}")
    print(f"Tasks with errors: {error_count}")
    print(f"Final tasks remaining: {len(final_tasks)}")
    print("==================================================")

if __name__ == "__main__":
    main()
