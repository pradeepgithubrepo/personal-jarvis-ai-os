import os
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

def main():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    opts = ClientOptions(schema="jarvis_insights_schemav1")
    client = create_client(url, key, options=opts)

    dummy_uuid = "00000000-0000-0000-0000-000000000000"

    print("Deleting from transaction_evidence via HTTP...")
    res_ev = client.table("transaction_evidence").delete().neq("evidence_id", dummy_uuid).execute()
    print(f"Deleted {len(res_ev.data or [])} evidence records.")

    print("Deleting from financial_transactions via HTTP...")
    res_tx = client.table("financial_transactions").delete().neq("transaction_id", dummy_uuid).execute()
    print(f"Deleted {len(res_tx.data or [])} transaction records.")

    print("Resetting signal_routes to PENDING for financial_agent...")
    res_route = (
        client.table("signal_routes")
        .update({
            "route_status": "PENDING",
            "completed_at": None,
            "error_message": None
        })
        .eq("agent_name", "financial_agent")
        .execute()
    )
    print(f"Reset {len(res_route.data or [])} routes back to PENDING.")

if __name__ == "__main__":
    main()
