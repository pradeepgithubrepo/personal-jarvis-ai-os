import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

print("--- Running Routing Layer Audits ---")

# 1. Lineage check: signal_routes -> understood_signals
res_sr_lineage = client.table("signal_routes").select("id, understood_signals:understood_signal_id(id)").execute()
sr_lineage_fails = sum(1 for row in res_sr_lineage.data if not row.get("understood_signals"))

# 2. Reason check: route_reason is not empty
res_sr_reason = client.table("signal_routes").select("id, route_reason").execute()
sr_reason_fails = sum(1 for row in res_sr_reason.data if not row.get("route_reason") or str(row.get("route_reason")).strip() == "")

# 3. Confidence check: route_confidence matches signal confidence
res_sr_conf = client.table("signal_routes").select("route_confidence, understood_signals:understood_signal_id(confidence)").execute()
sr_conf_fails = sum(1 for row in res_sr_conf.data if not row.get("understood_signals") or row["route_confidence"] != row["understood_signals"]["confidence"])

print(f"Audit results:")
print(f"  Lineage Failures:        {sr_lineage_fails} ({'✅ PASS' if sr_lineage_fails == 0 else '❌ FAIL'})")
print(f"  Route Reason Failures:   {sr_reason_fails} ({'✅ PASS' if sr_reason_fails == 0 else '❌ FAIL'})")
print(f"  Route Confidence Fails:  {sr_conf_fails} ({'✅ PASS' if sr_conf_fails == 0 else '❌ FAIL'})")

# 4. Action Safety Override verification:
# Find a sample signal where signal_type is ACTION and see its routes
res_sr_action = client.table("signal_routes").select("id, agent_name, route_reason, route_confidence, understood_signals:understood_signal_id(signal_type, summary)").eq("agent_name", "todo_agent").limit(3).execute()
print("\nSample Todo Dispatch Routes:")
for r in res_sr_action.data:
    us = r.get("understood_signals") or {}
    print(f"  Route ID: {r['id']}")
    print(f"    Signal Type: {us.get('signal_type')}")
    print(f"    Summary: {us.get('summary')}")
    print(f"    Route Reason: {r['route_reason']}")
    print(f"    Confidence: {r['route_confidence']}")

# 5. Multi-Route check:
# Find understood_signal_ids that have multiple routes (count > 1)
from collections import Counter
counts = Counter(r.get("understood_signals", {}).get("id") or r.get("understood_signal_id") for r in res_sr_lineage.data if r.get("understood_signals"))
multi_routes = [sid for sid, count in counts.items() if count > 1]
print(f"\nTotal Multi-Routed Signals: {len(multi_routes)}")
if multi_routes:
    print("Sample Multi-Routed Signal:")
    res_sample = client.table("signal_routes").select("agent_name, route_reason, understood_signals:understood_signal_id(signal_type, summary, contract_json)").eq("understood_signal_id", multi_routes[0]).execute()
    print(f"  Understood Signal ID: {multi_routes[0]}")
    if res_sample.data:
        us = res_sample.data[0].get("understood_signals") or {}
        print(f"    Type: {us.get('signal_type')}")
        print(f"    Summary: {us.get('summary')}")
        print(f"    Contract Keys: {list(us.get('contract_json', {}).keys())}")
        for r in res_sample.data:
            print(f"    -> Routed to: {r['agent_name']} (Reason: {r['route_reason']})")
