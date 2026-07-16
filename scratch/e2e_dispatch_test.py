"""E2E dispatch test for Phase 2B validation."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import uuid
from datetime import datetime, timezone
from supabase import create_client, ClientOptions
from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
opts = ClientOptions(schema="jarvis_insights_schemav1")
client = create_client(url, key, options=opts)

# --- Test canonical contracts ---
TEST_SIGNALS = [
    {
        "signal_type": "FINANCIAL", "importance": 0.9, "confidence": 0.95,
        "summary": "Debit INR 5000 UPI Amazon",
        "contract_json": {
            "contract_version": 1, "signal_type": "FINANCIAL",
            "importance": 0.9, "confidence": 0.95,
            "summary": "Debit INR 5000 UPI Amazon",
            "entities": ["Amazon"], "memory_candidate": False, "requires_action": False,
            "financial_candidate": True, "fact_candidate": False,
            "fyi_candidate": False, "noise_candidate": False,
            "type_specific": {"amount": 5000.0, "currency": "INR",
                              "transaction_type": "DEBIT", "payment_channel": "UPI", "merchant": "Amazon"},
        },
    },
    {
        "signal_type": "ACTION", "importance": 0.7, "confidence": 0.85,
        "summary": "Call plumber tomorrow",
        "contract_json": {
            "contract_version": 1, "signal_type": "ACTION",
            "importance": 0.7, "confidence": 0.85,
            "summary": "Call plumber tomorrow",
            "entities": [], "memory_candidate": True, "requires_action": True,
            "financial_candidate": False, "fact_candidate": False,
            "fyi_candidate": False, "noise_candidate": False,
            "type_specific": {"task_name": "Call plumber", "assignee": "Pradeep", "due_date": None},
        },
    },
    {
        "signal_type": "FYI", "importance": 0.5, "confidence": 0.9,
        "summary": "Flight AI-101 departure 8am",
        "contract_json": {
            "contract_version": 1, "signal_type": "FYI",
            "importance": 0.5, "confidence": 0.9,
            "summary": "Flight AI-101 departure 8am",
            "entities": ["Air India"], "memory_candidate": True, "requires_action": False,
            "financial_candidate": False, "fact_candidate": False,
            "fyi_candidate": True, "noise_candidate": False,
            "type_specific": {"event_name": "Flight AI-101", "event_time": "2026-07-12T08:00:00Z", "description": "Departure"},
        },
    },
    {
        "signal_type": "NOISE", "importance": 0.1, "confidence": 1.0,
        "summary": "Good morning message",
        "contract_json": {
            "contract_version": 1, "signal_type": "NOISE",
            "importance": 0.1, "confidence": 1.0,
            "summary": "Good morning message",
            "entities": [], "memory_candidate": False, "requires_action": False,
            "financial_candidate": False, "fact_candidate": False,
            "fyi_candidate": False, "noise_candidate": True,
            "type_specific": {},
        },
    },
    {
        "signal_type": "FINANCIAL", "importance": 0.88, "confidence": 0.9,
        "summary": "School fee INR 45000 to Lalaji Memorial",
        "contract_json": {
            "contract_version": 1, "signal_type": "FINANCIAL",
            "importance": 0.88, "confidence": 0.9,
            "summary": "School fee INR 45000 to Lalaji Memorial",
            "entities": ["Lalaji Memorial"], "memory_candidate": True, "requires_action": False,
            "financial_candidate": True, "fact_candidate": False,
            "fyi_candidate": False, "noise_candidate": False,
            "type_specific": {"amount": 45000.0, "currency": "INR",
                              "transaction_type": "DEBIT", "payment_channel": "NEFT",
                              "merchant": "Lalaji Memorial School"},
        },
    },
]

# Insert FK chain and test understood_signals
import random
inserted_ids = []
now = datetime.now(timezone.utc).isoformat()

for ts in TEST_SIGNALS:
    raw_id = random.randint(100000000, 999999999)
    try:
        client.table("mobile_signals").insert({
            "id": raw_id, "device_id": "e2e_phase2b", "source": "e2e_test",
            "sender": "TESTER", "message": "E2E Phase 2B test",
            "mobile_timestamp": now, "message_hash": str(uuid.uuid4()), "processed": False,
        }).execute()
    except Exception as e:
        print(f"Failed to insert mobile_signal: {e}")
        continue

    qualified_id = str(uuid.uuid4())
    try:
        client.table("qualified_signals").insert({
            "id": qualified_id, "signal_id": raw_id, "source": "e2e_test",
            "sender": "TESTER", "message": "E2E Phase 2B test",
            "timestamp": now, "qualification_score": 95.0, "qualification_status": "QUALIFIED",
        }).execute()
    except Exception as e:
        print(f"Failed to insert qualified_signal: {e}")
        continue

    uid = str(uuid.uuid4())
    try:
        client.table("understood_signals").insert({
            "id": uid, "qualified_signal_id": qualified_id, "raw_signal_id": raw_id,
            "signal_type": ts["signal_type"], "importance": ts["importance"],
            "confidence": ts["confidence"], "summary": ts["summary"],
            "processing_path": "e2e_test", "contract_json": ts["contract_json"], "is_verified": False,
        }).execute()
        inserted_ids.append((uid, ts["signal_type"]))
    except Exception as e:
        print(f"Failed to insert understood_signal: {e}")
        continue

print(f"Inserted {len(inserted_ids)} understood_signals")

# Route and dispatch
router = SignalRouter()
dispatcher = ContractDispatcher()
dispatch_summary = {}

for uid, sig_type in inserted_ids:
    res = client.table("understood_signals").select("*").eq("id", uid).limit(1).execute()
    sig = res.data[0]
    decision = router.route(sig)
    result = dispatcher.dispatch(decision, supabase_client=client)
    status = result.overall_status
    dispatch_summary[status] = dispatch_summary.get(status, 0) + 1
    print(f"  type={sig_type:12s}  route={str(decision.route_to):45s}  status={status}")

print("\n=== Dispatch Summary ===")
for s, c in dispatch_summary.items():
    print(f"  {s}: {c}")

# Verify signal_routes
routes = client.table("signal_routes").select("agent_name,route_status").execute()
print(f"\nsignal_routes total rows: {len(routes.data)}")
agent_counts = {}
for row in routes.data:
    k = f"{row['agent_name']}:{row['route_status']}"
    agent_counts[k] = agent_counts.get(k, 0) + 1
for k, cnt in sorted(agent_counts.items()):
    print(f"  {k}: {cnt}")

# Cleanup (Disabled for operational audit verification)
# client.table("mobile_signals").delete().eq("id", raw_id).execute()
# print("\nCleanup done.")

