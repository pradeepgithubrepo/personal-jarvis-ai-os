import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

def main():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    opts = ClientOptions(schema="jarvis_insights_schemav1")
    client = create_client(url, key, options=opts)

    print("Fetching data from database...")

    # Fetch all data
    mobile_res = client.table("mobile_signals").select("*").execute()
    mobile_signals = mobile_res.data or []

    qualified_res = client.table("qualified_signals").select("*").execute()
    qualified_signals = qualified_res.data or []

    understood_res = client.table("understood_signals").select("*").execute()
    understood_signals = understood_res.data or []

    routes_res = client.table("signal_routes").select("*").execute()
    signal_routes = routes_res.data or []

    tasks_res = client.table("tasks").select("*").execute()
    tasks = tasks_res.data or []

    print(f"Loaded:")
    print(f"  - {len(mobile_signals)} mobile_signals")
    print(f"  - {len(qualified_signals)} qualified_signals")
    print(f"  - {len(understood_signals)} understood_signals")
    print(f"  - {len(signal_routes)} signal_routes")
    print(f"  - {len(tasks)} tasks")

    # Mappings
    mobile_map = {m["id"]: m for m in mobile_signals}
    # Some qualified signals reference mobile_signals.id via signal_id or message_hash?
    # Let's map qualified by ID and message_hash
    qualified_map = {q["id"]: q for q in qualified_signals}
    understood_map = {u["id"]: u for u in understood_signals}
    routes_map = {r["id"]: r for r in signal_routes}

    # Group routes by understood_signal_id
    routes_by_us = {}
    for r in signal_routes:
        us_id = r["understood_signal_id"]
        routes_by_us.setdefault(us_id, []).append(r)

    # Let's map understood signals to qualified signals
    # Understood has qualified_signal_id or raw_signal_id
    us_by_qs = {}
    for u in understood_signals:
        qs_id = u.get("qualified_signal_id")
        if qs_id:
            us_by_qs.setdefault(qs_id, []).append(u)

    # Let's map qualified signals to mobile signals
    # qualified_signals has signal_id (references mobile_signals.id?)
    qs_by_ms = {}
    for q in qualified_signals:
        ms_id = q.get("signal_id")
        if ms_id:
            qs_by_ms.setdefault(ms_id, []).append(q)

    # Analyse tasks
    # 1. Directly created tasks (tasks with route_id)
    task_by_route = {}
    for t in tasks:
        r_id = t.get("route_id")
        if r_id:
            task_by_route.setdefault(r_id, []).append(t)

    # 2. Merged tasks (tasks whose description contains "Merged route_id:" or similar)
    merged_routes_to_tasks = {}
    for t in tasks:
        desc = t.get("description") or ""
        # Let's look for UUIDs of routes in the description
        for r in signal_routes:
            r_id = r["id"]
            if r_id in desc:
                merged_routes_to_tasks.setdefault(r_id, []).append(t)

    # Let's perform a step-by-step analysis:
    # We want to understand what was persisted to the tasks table, what was dropped and why.

    print("\n--- PHASE 1: MOBILE SIGNALS -> QUALIFIED SIGNALS ---")
    disqualified_signals = []
    unprocessed_mobile = []
    for ms in mobile_signals:
        qs_list = qs_by_ms.get(ms["id"], [])
        if not qs_list:
            # Let's check by message_hash if signal_id is empty or not matching
            qs_list = [q for q in qualified_signals if q.get("message_hash") == ms.get("message_hash")]
        
        if not qs_list:
            if ms.get("processed") is False:
                unprocessed_mobile.append(ms)
            else:
                disqualified_signals.append(ms)
        else:
            for qs in qs_list:
                if qs["qualification_status"] != "QUALIFIED":
                    disqualified_signals.append((ms, qs))

    print(f"Total Mobile Signals: {len(mobile_signals)}")
    print(f"Disqualified/Skipped Signals: {len(disqualified_signals)}")
    print(f"Unprocessed Mobile Signals: {len(unprocessed_mobile)}")

    print("\n--- PHASE 2: QUALIFIED SIGNALS -> UNDERSTOOD SIGNALS ---")
    not_understood = []
    for qs in qualified_signals:
        if qs["qualification_status"] == "QUALIFIED":
            us_list = us_by_qs.get(qs["id"], [])
            if not us_list:
                # check by message_hash
                us_list = [u for u in understood_signals if u.get("message_hash") == qs.get("message_hash")]
            if not us_list:
                not_understood.append(qs)
    print(f"Qualified Signals: {len([q for q in qualified_signals if q['qualification_status'] == 'QUALIFIED'])}")
    print(f"Qualified but NOT Understood (dropped before routing): {len(not_understood)}")
    for q in not_understood:
        print(f"  - [{q['id']}] Source: {q['source']} | Sender: {q['sender']} | Message: {q['message'][:80]}")

    print("\n--- PHASE 3: UNDERSTOOD SIGNALS -> ROUTES ---")
    unrouted_understood = []
    for us in understood_signals:
        routes = routes_by_us.get(us["id"], [])
        if not routes:
            unrouted_understood.append(us)
    print(f"Understood Signals: {len(understood_signals)}")
    print(f"Understood but NOT Routed: {len(unrouted_understood)}")
    for u in unrouted_understood:
        print(f"  - [{u['id']}] Summary: {u['summary']} | Reason: {u.get('reason') or 'No reason given'}")

    print("\n--- PHASE 4: ROUTES -> TASKS (PERSISTED VS DROPPED) ---")
    print(f"Total Routes: {len(signal_routes)}")
    
    route_summary = []
    for r in signal_routes:
        us = understood_map.get(r["understood_signal_id"])
        qs = None
        if us:
            qs = qualified_map.get(us.get("qualified_signal_id"))
            if not qs:
                # try finding by message_hash
                for q in qualified_signals:
                    if q.get("message_hash") == us.get("message_hash"):
                        qs = q
                        break

        # Check outcomes
        created_tasks = task_by_route.get(r["id"], [])
        merged_tasks = merged_routes_to_tasks.get(r["id"], [])
        
        status = r["route_status"]
        outcome = "UNKNOWN"
        detail = ""

        if status == "PENDING":
            outcome = "PENDING"
            detail = "Awaiting agent execution"
        elif status == "FAILED":
            outcome = "FAILED"
            detail = f"Execution failed: {r.get('error_message')}"
        elif status == "COMPLETED":
            if created_tasks:
                outcome = "PERSISTED (CREATED)"
                detail = ", ".join([f"Task: '{t['title']}' (ID: {t['id']})" for t in created_tasks])
            elif merged_tasks:
                outcome = "PERSISTED (MERGED)"
                detail = ", ".join([f"Merged into Task: '{t['title']}' (ID: {t['id']})" for t in merged_tasks])
            else:
                outcome = "DROPPED (IGNORED)"
                detail = f"Classified as IGNORE by todo_agent. Route reason: {r.get('route_reason')}"
        else:
            outcome = f"ROUTE_{status}"
            detail = f"Route status is {status}. Route reason: {r.get('route_reason')}"

        route_summary.append({
            "route_id": r["id"],
            "agent_name": r["agent_name"],
            "status": status,
            "outcome": outcome,
            "detail": detail,
            "message": qs["message"] if qs else (us["summary"] if us else "Unknown Signal"),
            "summary": us["summary"] if us else "Unknown",
            "type": us["signal_type"] if us else "Unknown",
            "confidence": us["confidence"] if us else 0.0,
            "importance": us["importance"] if us else 0.0,
            "route_reason": r.get("route_reason") or ""
        })

    # Group by outcome
    by_outcome = {}
    for rs in route_summary:
        by_outcome.setdefault(rs["outcome"], []).append(rs)

    for outcome, list_rs in by_outcome.items():
        print(f"\nOutcome: {outcome} (Count: {len(list_rs)})")
        for rs in list_rs:
            print(f"  - Agent: {rs['agent_name']} | Type: {rs['type']} | Conf: {rs['confidence']:.2f}")
            print(f"    Message: {rs['message'][:100]}")
            print(f"    Details: {rs['detail']}")

    # Write full breakdown to JSON for reference
    with open("scratch/full_analysis_breakdown.json", "w") as f:
        json.dump(route_summary, f, indent=2)

if __name__ == "__main__":
    main()
