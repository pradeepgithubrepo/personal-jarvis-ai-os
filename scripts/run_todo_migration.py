"""
scripts/run_todo_migration.py

One-time database migration script to correct ToDo ownership assignment.
Reclassifies the 'assigned_to' field for all existing tasks to PRADEEP, SHOBANA, or BOTH
based on content keywords and originating device metadata.
"""
import os
import sys
import re
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Keywords lists
SCHOOL_KEYWORDS = [
    "school", "preschool", "daycare", "parent meeting", "homework", 
    "school fees", "school events", "parent teacher meeting", "parent-teacher meeting"
]

KIDS_KEYWORDS = [
    "charan", "chainicka", "child", "kids", "children", "vaccination", 
    "medical appointment", "shopping for children", "child activities",
    "family activity", "family activities", "parent feedback"
]

def determine_by_text(title: str, description: str) -> str:
    text = (title + " " + (description or "")).lower()
    
    # Rule 1: School related -> BOTH
    if any(k in text for k in SCHOOL_KEYWORDS):
        return "BOTH"
        
    # Rule 2: Kids/Family related -> BOTH
    if any(k in text for k in KIDS_KEYWORDS):
        return "BOTH"
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Ingest/migrate ToDo assignment values")
    parser.add_argument("--write", action="store_true", help="Perform actual database updates")
    args = parser.parse_args()

    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    print("Fetching all tasks...")
    try:
        tasks_res = client.table("tasks").select("*").execute()
        tasks = tasks_res.data or []
    except Exception as e:
        print(f"ERROR: Failed to fetch tasks: {e}")
        sys.exit(1)

    print(f"Loaded {len(tasks)} tasks.")

    report = {
        "total": len(tasks),
        "PRADEEP": 0,
        "SHOBANA": 0,
        "BOTH": 0,
        "UNRESOLVED": 0,
        "records": []
    }

    unresolved_list = []
    update_list = []

    for task in tasks:
        task_id = task["id"]
        title = task["title"]
        description = task.get("description") or ""
        route_id = task.get("route_id")
        current_assignee = task.get("assigned_to")

        # 1. Evaluate content keywords first
        assigned_to = determine_by_text(title, description)

        reason = "Keyword match (School/Kids)"
        device_id = None

        # 2. Trace device via route_id if not resolved by keywords
        if not assigned_to:
            target_route = route_id
            
            # Fallback: Extract route ID from description if present
            if not target_route and description:
                match = re.search(r"Ref: Signal Route id:\s*([a-f0-9\-]{36})", description, re.IGNORECASE)
                if match:
                    target_route = match.group(1)
                    reason = f"Extracted Route ID {target_route[:8]} from description"
                else:
                    # Also look for any UUID pattern if it indicates a route
                    match_uuid = re.search(r"route_id:\s*([a-f0-9\-]{36})", description, re.IGNORECASE)
                    if match_uuid:
                        target_route = match_uuid.group(1)
                        reason = f"Extracted Route ID {target_route[:8]} from system updates"

            if target_route:
                try:
                    route_res = client.table("signal_routes").select("understood_signal_id").eq("id", target_route).execute()
                    if route_res.data:
                        us_id = route_res.data[0]["understood_signal_id"]
                        us_res = client.table("understood_signals").select("device_id").eq("id", us_id).execute()
                        if us_res.data:
                            device_id = us_res.data[0]["device_id"]
                except Exception as e:
                    pass

            if device_id:
                dev_lower = device_id.lower()
                if "shobana" in dev_lower:
                    assigned_to = "SHOBANA"
                    reason = f"Traced to Shobana's phone ({device_id})"
                elif "pradeep" in dev_lower:
                    assigned_to = "PRADEEP"
                    reason = f"Traced to Pradeep's phone ({device_id})"

        # 3. Handle unresolved -> Fallback to PRADEEP
        if not assigned_to:
            assigned_to = "PRADEEP"
            reason = "No matching evidence (Manual Review Fallback to PRADEEP)"
            unresolved_list.append((task_id, title, description, current_assignee))
            report["UNRESOLVED"] += 1
            report[assigned_to] += 1
            update_list.append((task_id, title, assigned_to, reason))
        else:
            report[assigned_to] += 1
            update_list.append((task_id, title, assigned_to, reason))

        report["records"].append({
            "task_id": task_id,
            "title": title,
            "previous_assigned": current_assignee,
            "proposed_assigned": assigned_to or "REQUIRES MANUAL REVIEW",
            "reason": reason
        })

    # Output Migration Report
    print("\n==================================================")
    print("           TO-DO MIGRATION REPORT")
    print("==================================================")
    print(f"Total ToDos Processed:            {report['total']}")
    print(f"Assigned to PRADEEP:              {report['PRADEEP']}")
    print(f"Assigned to SHOBANA:              {report['SHOBANA']}")
    print(f"Assigned to BOTH:                 {report['BOTH']}")
    print(f"Records requiring manual review:  {report['UNRESOLVED']}")
    print("==================================================\n")

    if unresolved_list:
        print("--- RECORDS REQUIRING MANUAL REVIEW ---")
        for u in unresolved_list:
            print(f"ID: {u[0]} | Title: {u[1]} | Current: {u[3]}")
        print("---------------------------------------\n")

    if args.write:
        print(f"Performing actual updates for {len(update_list)} tasks...")
        updated_count = 0
        for task_id, title, target_assignee, reason in update_list:
            try:
                client.table("tasks").update({"assigned_to": target_assignee}).eq("id", task_id).execute()
                print(f"✓ Updated '{title[:30]}' -> {target_assignee} ({reason})")
                updated_count += 1
            except Exception as e:
                print(f"✗ Failed to update task {task_id} ({title}): {e}")
        print(f"\nSuccessfully migrated {updated_count} tasks in the database.")
    else:
        print("DRY-RUN COMPLETE. No database updates were made. Run with '--write' to execute.")

if __name__ == "__main__":
    main()
