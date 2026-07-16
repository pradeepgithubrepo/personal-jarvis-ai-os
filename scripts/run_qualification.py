import os
import sys
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.consumer.qualification_agent import SignalQualificationAgent

def main():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)
    
    print("Fetching unprocessed mobile signals...")
    res = client.table("mobile_signals").select("*").eq("processed", False).order("id").execute()
    unprocessed_signals = res.data
    
    total_unprocessed = len(unprocessed_signals)
    print(f"Found {total_unprocessed} unprocessed signals.")
    
    if not unprocessed_signals:
        print("No unprocessed signals found. Database is up to date.")
        sys.exit(0)
        
    agent = SignalQualificationAgent(config_dir="config")
    
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc).isoformat()
    
    # Insert pipeline run
    client.table("pipeline_runs").insert({
        "run_id": str(run_id),
        "pipeline_name": "qualification_sync",
        "phase": "phase2_qualification_v2",
        "trigger_type": "MANUAL",
        "started_at": started_at,
        "status": "STARTED",
        "host_name": "JarvisRecovery",
        "user_name": "prad",
        "version": "v2.1.0-backfill",
        "metadata": {"description": "Qualified signals backfill"}
    }).execute()
    
    qualified_inserts = []
    mobile_signal_updates = []
    
    # Metrics
    stats = {
        "qualified": 0,
        "review": 0,
        "rejected": 0,
        "sources": {},
        "dates": []
    }
    
    print("Processing qualification...")
    for sig in unprocessed_signals:
        outcome = agent.qualify_signal(sig)
        status = outcome["status"] # QUALIFIED, REVIEW, REJECTED
        
        # Track status count
        if status == "QUALIFIED":
            stats["qualified"] += 1
        elif status == "REVIEW":
            stats["review"] += 1
        else:
            stats["rejected"] += 1
            
        # Track source count
        src = sig.get("source") or "unknown"
        stats["sources"][src] = stats["sources"].get(src, 0) + 1
        
        if sig.get("mobile_timestamp"):
            stats["dates"].append(sig["mobile_timestamp"])
            
        # Construct row
        qualified_inserts.append({
            "id": str(uuid.uuid4()),
            "signal_id": sig["id"],
            "source": sig["source"],
            "sender": sig["sender"],
            "message": sig["message"],
            "timestamp": sig["mobile_timestamp"],
            "device_id": sig["device_id"],
            "message_hash": sig["message_hash"],
            "metadata": outcome["canonical_metadata"],
            "qualification_score": outcome["score"],
            "qualification_status": outcome["status"],
            "qualification_reason": outcome["reason"],
            "amount": outcome["amount"],
            "currency": outcome["currency"],
            "transaction_type": outcome["transaction_type"]
        })
        
        mobile_signal_updates.append(sig["id"])
        
    print(f"Bulk inserting {len(qualified_inserts)} rows into qualified_signals...")
    chunk_size = 100
    for i in range(0, len(qualified_inserts), chunk_size):
        chunk = qualified_inserts[i:i + chunk_size]
        client.table("qualified_signals").insert(chunk).execute()
        
    print("Bulk updating processed flags in mobile_signals...")
    for i in range(0, len(mobile_signal_updates), chunk_size):
        chunk_ids = mobile_signal_updates[i:i + chunk_size]
        client.table("mobile_signals").update({"processed": True}).in_("id", chunk_ids).execute()
        
    # Complete pipeline run
    client.table("pipeline_runs").update({
        "status": "SUCCESS",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int((datetime.now(timezone.utc) - datetime.fromisoformat(started_at)).total_seconds() * 1000),
        "metadata": {
            "signals_processed": total_unprocessed,
            "qualified": stats["qualified"],
            "review": stats["review"],
            "rejected": stats["rejected"]
        }
    }).eq("run_id", str(run_id)).execute()
    
    # Calculate date coverage
    min_date = "N/A"
    max_date = "N/A"
    if stats["dates"]:
        parsed_dates = []
        for d in stats["dates"]:
            try:
                clean_d = d.replace("Z", "").split("+")[0]
                parsed_dates.append(datetime.fromisoformat(clean_d))
            except Exception:
                pass
        if parsed_dates:
            min_date = min(parsed_dates).strftime("%Y-%m-%d %H:%M:%S UTC")
            max_date = max(parsed_dates).strftime("%Y-%m-%d %H:%M:%S UTC")
            
    # Print summary report
    print("\n" + "="*50)
    print("QUALIFIED_SIGNALS_RECOVERY_SUMMARY")
    print("="*50)
    print(f"Total Mobile Signals Evaluated: {total_unprocessed}")
    print(f"Qualified Signals Created:      {stats['qualified']}")
    print(f"Review Signals Created:         {stats['review']}")
    print(f"Rejected Signals Created:       {stats['rejected']}")
    print("-" * 50)
    print("Source Distribution of Evaluated Signals:")
    for src_name, count in sorted(stats["sources"].items()):
        print(f"  {src_name}: {count}")
    print("-" * 50)
    print(f"Date Coverage: {min_date} to {max_date}")
    print("="*50)

if __name__ == "__main__":
    main()
