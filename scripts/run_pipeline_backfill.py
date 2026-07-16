import os
import sys
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from loguru import logger

# Insert workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.consumer.qualification_agent import SignalQualificationAgent
from src.agents.sua.orchestrator import run_pipeline as run_sua_pipeline
from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher

def main():
    load_dotenv()
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Connection")
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing from environment variables.")
        print("Impact: Pipeline backfill cannot connect to the database.")
        print("Recommended Resolution: Set the environment variables in .env.")
        sys.exit(1)
        
    try:
        # Initialize Supabase client
        options = ClientOptions(schema="jarvis_insights_schemav1")
        client: Client = create_client(supabase_url, supabase_key, options=options)
    except Exception as e:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Client Initialization")
        print(f"Error: {e}")
        print("Impact: Pipeline backfill cannot connect to Supabase.")
        print("Recommended Resolution: Check connectivity to Supabase.")
        sys.exit(1)

    print("Checking initial counts...")
    try:
        count_ms_before = client.table('mobile_signals').select('count', count='exact').limit(0).execute().count
        count_qs_before = client.table('qualified_signals').select('count', count='exact').limit(0).execute().count
        count_us_before = client.table('understood_signals').select('count', count='exact').limit(0).execute().count
        count_sr_before = client.table('signal_routes').select('count', count='exact').limit(0).execute().count
    except Exception as e:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Initial Count Query")
        print(f"Error: {e}")
        print("Impact: Failed to read from Supabase tables.")
        print("Recommended Resolution: Ensure table permissions are correct and the schema exists.")
        sys.exit(1)

    print(f"Initial counts:")
    print(f"  mobile_signals:     {count_ms_before}")
    print(f"  qualified_signals:  {count_qs_before}")
    print(f"  understood_signals: {count_us_before}")
    print(f"  signal_routes:      {count_sr_before}")

    # Step 1: Run Qualification Agent V2
    print("\n--- Running Stage 1: Qualification Agent V2 ---")
    try:
        # Find unprocessed mobile signals
        res = client.table("mobile_signals").select("*").eq("processed", False).order("id").execute()
        unprocessed_signals = res.data
        print(f"Found {len(unprocessed_signals)} unprocessed signals in mobile_signals.")
        
        if unprocessed_signals:
            agent = SignalQualificationAgent(config_dir="config")
            
            # Start pipeline run log for Qualification
            run_id = uuid.uuid4()
            started_at = datetime.now(timezone.utc).isoformat()
            
            # Insert pipeline run
            run_row = {
                "run_id": str(run_id),
                "pipeline_name": "qualification_sync",
                "phase": "phase2_qualification_v2",
                "trigger_type": "MANUAL",
                "started_at": started_at,
                "status": "STARTED",
                "host_name": "jarvis-backfill",
                "user_name": "prad",
                "version": "v2.1.0-backfill",
                "metadata": {}
            }
            client.table("pipeline_runs").insert(run_row).execute()
            
            qualified_inserts = []
            mobile_signal_updates = []
            
            for sig in unprocessed_signals:
                outcome = agent.qualify_signal(sig)
                
                # Construct qualified_signals row
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
                
                # Mark as processed
                mobile_signal_updates.append(sig["id"])

            # Bulk insert qualified_signals
            chunk_size = 100
            for i in range(0, len(qualified_inserts), chunk_size):
                chunk = qualified_inserts[i:i + chunk_size]
                client.table("qualified_signals").insert(chunk).execute()
                
            # Bulk update processed flag in mobile_signals
            for i in range(0, len(mobile_signal_updates), chunk_size):
                chunk_ids = mobile_signal_updates[i:i + chunk_size]
                client.table("mobile_signals").update({"processed": True}).in_("id", chunk_ids).execute()
            
            # Complete pipeline run
            client.table("pipeline_runs").update({
                "status": "SUCCESS",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": int((datetime.now(timezone.utc) - datetime.fromisoformat(started_at)).total_seconds() * 1000),
                "metadata": {
                    "signals_processed": len(unprocessed_signals),
                    "qualified": len([x for x in qualified_inserts if x["qualification_status"] == "QUALIFIED"]),
                    "review": len([x for x in qualified_inserts if x["qualification_status"] == "REVIEW"]),
                    "rejected": len([x for x in qualified_inserts if x["qualification_status"] == "REJECTED"])
                }
            }).eq("run_id", str(run_id)).execute()
            
            print(f"Qualification Stage complete. Processed: {len(unprocessed_signals)}")
        else:
            print("No unprocessed signals to qualify.")
            
    except Exception as e:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Stage 1 Qualification Agent")
        print(f"Error: {e}")
        print("Impact: Qualification stage aborted.")
        sys.exit(1)

    # Step 2: Run Signal Understanding Agent (SUA)
    print("\n--- Running Stage 2: Signal Understanding Agent ---")
    try:
        result = run_sua_pipeline(client, trigger_type="MANUAL", model_name="qwen2.5:1.5b")
        print("SUA Stage complete.")
        print(f"  Processed: {result.get('signals_processed')}")
        print(f"  Understood: {result.get('signals_understood')}")
        print(f"  Failed: {result.get('signals_failed')}")
        if result.get("status") == "FAILED":
            raise Exception(result.get("error_message") or "Unknown error in SUA pipeline")
            
    except Exception as e:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Stage 2 Signal Understanding Agent")
        print(f"Error: {e}")
        print("Impact: Signal understanding stage aborted.")
        sys.exit(1)

    # Step 3: Router
    print("\n--- Running Stage 3: Signal Router ---")
    try:
        # Fetch all understood signals
        res_us = client.table("understood_signals").select("*").execute()
        understood_signals = res_us.data
        print(f"Routing {len(understood_signals)} signals...")
        
        router = SignalRouter()
        dispatcher = ContractDispatcher()
        
        for us in understood_signals:
            route_decision = router.route(us)
            dispatcher.dispatch(route_decision, client)
            
        print("Routing Stage complete.")
        
        # Ingest pending to-do items using the real TodoAgent
        print("\n--- Running To-Do Agent Ingestion Worker ---")
        from src.agents.todo.todo_agent import TodoAgent
        todo_agent = TodoAgent()
        todo_agent.process_pending_routes(client)
        print("To-Do Agent Ingestion Worker complete.")
    except Exception as e:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Stage 3 Signal Router")
        print(f"Error: {e}")
        print("Impact: Signal routing stage aborted.")
        sys.exit(1)

    # Validation and reporting
    print("\n--- Pipeline Backfill Complete. Fetching Final Counts ---")
    try:
        count_ms_after = client.table('mobile_signals').select('count', count='exact').limit(0).execute().count
        count_qs_after = client.table('qualified_signals').select('count', count='exact').limit(0).execute().count
        count_us_after = client.table('understood_signals').select('count', count='exact').limit(0).execute().count
        count_sr_after = client.table('signal_routes').select('count', count='exact').limit(0).execute().count
        
        # --- Run Qualification Validation Queries ---
        # 1. Metadata Preservation check
        res_meta_check_null = client.table("qualified_signals").select("id").in_("qualification_status", ["QUALIFIED", "REVIEW"]).is_("metadata", "null").execute()
        res_meta_check_empty = client.table("qualified_signals").select("id").in_("qualification_status", ["QUALIFIED", "REVIEW"]).eq("metadata", "{}").execute()
        meta_fails = len(res_meta_check_null.data) + len(res_meta_check_empty.data)
                
        # 2. Device ID Preservation check
        res_device_check = client.table("qualified_signals").select("device_id, mobile_signals:signal_id(device_id)").execute()
        device_fails = sum(1 for row in res_device_check.data if not row.get("mobile_signals") or row["device_id"] != row["mobile_signals"]["device_id"])
                
        # 3. Message Hash check
        res_hash_check = client.table("qualified_signals").select("message_hash, mobile_signals:signal_id(message_hash)").execute()
        hash_fails = sum(1 for row in res_hash_check.data if not row.get("mobile_signals") or row["message_hash"] != row["mobile_signals"]["message_hash"])

        # 4. Financial metadata check
        res_fin_check = client.table("qualified_signals").select("amount, metadata").eq("qualification_status", "QUALIFIED").in_("source", ["gpay", "bank_statement"]).execute()
        fin_fails = 0
        for row in res_fin_check.data:
            meta = row.get("metadata") or {}
            try:
                meta_amount = float(str(meta.get("source_metadata", {}).get("amount", 0)).replace("$", "").replace(",", ""))
            except Exception:
                meta_amount = 0.0
            if row.get("amount") is None or float(row["amount"]) != meta_amount:
                fin_fails += 1

        # 5. Lineage check
        res_lineage_check = client.table("qualified_signals").select("id, mobile_signals:signal_id(id)").execute()
        lineage_fails = sum(1 for row in res_lineage_check.data if not row.get("mobile_signals"))


        # --- Run Understanding Validation Queries ---
        # 1. Metadata Preservation check
        res_us_meta_null = client.table("understood_signals").select("id").is_("metadata", "null").execute()
        res_us_meta_empty = client.table("understood_signals").select("id").eq("metadata", "{}").execute()
        us_meta_fails = len(res_us_meta_null.data) + len(res_us_meta_empty.data)

        # 2. Device ID Preservation check
        res_us_device = client.table("understood_signals").select("device_id, qualified_signals:qualified_signal_id(device_id)").execute()
        us_device_fails = sum(1 for row in res_us_device.data if not row.get("qualified_signals") or row["device_id"] != row["qualified_signals"]["device_id"])

        # 3. Message Hash check
        res_us_hash = client.table("understood_signals").select("message_hash, qualified_signals:qualified_signal_id(message_hash)").execute()
        us_hash_fails = sum(1 for row in res_us_hash.data if not row.get("qualified_signals") or row["message_hash"] != row["qualified_signals"]["message_hash"])

        # 4. Lineage check
        res_us_lineage = client.table("understood_signals").select("id, qualified_signals:qualified_signal_id(id)").execute()
        us_lineage_fails = sum(1 for row in res_us_lineage.data if not row.get("qualified_signals"))

        # --- Run Routing Validation Queries ---
        # 1. Routing Lineage check
        res_sr_lineage = client.table("signal_routes").select("id, understood_signals:understood_signal_id(id)").execute()
        sr_lineage_fails = sum(1 for row in res_sr_lineage.data if not row.get("understood_signals"))

        # 2. Reason check
        res_sr_reason = client.table("signal_routes").select("id, route_reason").execute()
        sr_reason_fails = sum(1 for row in res_sr_reason.data if not row.get("route_reason"))

        # 3. Confidence check
        res_sr_conf = client.table("signal_routes").select("route_confidence, understood_signals:understood_signal_id(confidence)").execute()
        sr_conf_fails = sum(1 for row in res_sr_conf.data if not row.get("understood_signals") or row["route_confidence"] != row["understood_signals"]["confidence"])

        # Get Understood Signal Type breakdown from understood_signals
        res_us_all = client.table("understood_signals").select("signal_type").execute()
        from collections import Counter
        us_type_counts = Counter(r["signal_type"] for r in res_us_all.data)
        
        # Get 10 sample records from understood_signals
        res_us_samples = client.table("understood_signals").select("*").limit(10).execute()
        
    except Exception as e:
        print("SUPABASE_BLOCKER DETECTED")
        print("Operation: Final Validation Query")
        print(f"Error: {e}")
        print("Impact: Failed to fetch final counts for report.")
        sys.exit(1)

    # Write reports
    report_paths = [
        "PIPELINE_BACKFILL_EXECUTION_REPORT.md",
        "docs/v2/understanding_layer/PIPELINE_BACKFILL_EXECUTION_REPORT.md"
    ]
    
    # Ensure directory exists
    os.makedirs("docs/v2/understanding_layer", exist_ok=True)
    
    for report_path in report_paths:
        with open(report_path, "w") as f:
            f.write("# PIPELINE BACKFILL EXECUTION REPORT — JARVIS V2 (UNDERSTANDING BOUNDARY)\n\n")
            f.write(f"Executed At: {datetime.now(timezone.utc).isoformat()}\n")
            f.write("Status: **SUCCESS (QUALIFICATION, UNDERSTANDING & ROUTING INGESTED)**\n\n")
            
            f.write("## 1. Table Row Counts\n\n")
            f.write("| Table | Rows Before | Rows After |\n")
            f.write("|---|---|---|\n")
            f.write(f"| `mobile_signals` | {count_ms_before} | {count_ms_after} |\n")
            f.write(f"| `qualified_signals` | {count_qs_before} | {count_qs_after} |\n")
            f.write(f"| `understood_signals` | {count_us_before} | {count_us_after} |\n")
            f.write(f"| `signal_routes` | {count_sr_before} | {count_sr_after} |\n\n")
            
            f.write("## 2. Understood Signal Type Breakdown\n\n")
            f.write(f"- **FINANCIAL count**: {us_type_counts.get('FINANCIAL', 0)}\n")
            f.write(f"- **ACTION count**: {us_type_counts.get('ACTION', 0)}\n")
            f.write(f"- **FYI count**: {us_type_counts.get('FYI', 0)}\n")
            f.write(f"- **FACT count**: {us_type_counts.get('FACT', 0)}\n")
            f.write(f"- **NOISE count**: {us_type_counts.get('NOISE', 0)}\n\n")
            
            f.write("## 3. Post-Rebuild Validation Metrics (Audits)\n\n")
            f.write("### 3.1 Qualification Layer Audits\n\n")
            f.write("| Validation Check | Failures | Status |\n")
            f.write("|---|---|---|\n")
            f.write(f"| Metadata Preservation Check | {meta_fails} | {'✅ PASS' if meta_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Device ID Preservation Check | {device_fails} | {'✅ PASS' if device_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Message Hash Preservation Check | {hash_fails} | {'✅ PASS' if hash_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Financial Metadata Check | {fin_fails} | {'✅ PASS' if fin_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Lineage Preservation Check | {lineage_fails} | {'✅ PASS' if lineage_fails == 0 else '❌ FAIL'} |\n\n")
            
            f.write("### 3.2 Understanding Layer Audits\n\n")
            f.write("| Validation Check | Failures | Status |\n")
            f.write("|---|---|---|\n")
            f.write(f"| Metadata Preservation Check | {us_meta_fails} | {'✅ PASS' if us_meta_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Device ID Preservation Check | {us_device_fails} | {'✅ PASS' if us_device_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Message Hash Preservation Check | {us_hash_fails} | {'✅ PASS' if us_hash_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Lineage Preservation Check | {us_lineage_fails} | {'✅ PASS' if us_lineage_fails == 0 else '❌ FAIL'} |\n\n")

            f.write("### 3.3 Routing Layer Audits\n\n")
            f.write("| Validation Check | Failures | Status |\n")
            f.write("|---|---|---|\n")
            f.write(f"| Lineage Check (FK constraints) | {sr_lineage_fails} | {'✅ PASS' if sr_lineage_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Route Reason Check (Non-empty reason) | {sr_reason_fails} | {'✅ PASS' if sr_reason_fails == 0 else '❌ FAIL'} |\n")
            f.write(f"| Route Confidence Check (Match Signal) | {sr_conf_fails} | {'✅ PASS' if sr_conf_fails == 0 else '❌ FAIL'} |\n\n")

            f.write("## 4. Sample Understood Records (10 Samples)\n\n")
            if res_us_samples.data:
                for idx, item in enumerate(res_us_samples.data):
                    f.write(f"### Sample {idx + 1}\n")
                    f.write(f"- **ID**: `{item.get('id')}`\n")
                    f.write(f"- **Qualified ID (FK)**: `{item.get('qualified_signal_id')}`\n")
                    f.write(f"- **Source Raw ID**: `{item.get('raw_signal_id')}`\n")
                    f.write(f"- **Signal Type**: `{item.get('signal_type')}`\n")
                    f.write(f"- **Confidence**: {item.get('confidence')}\n")
                    f.write(f"- **Processing Path**: `{item.get('processing_path')}`\n")
                    f.write(f"- **Device ID**: `{item.get('device_id')}`\n")
                    f.write(f"- **Message Hash**: `{item.get('message_hash')}`\n")
                    f.write(f"- **Summary**: *{item.get('summary')}*\n")
                    f.write(f"- **Contract Schema JSON (`contract_json`)**:\n")
                    f.write(f"```json\n{json.dumps(item.get('contract_json'), indent=2)}\n```\n")
                    f.write(f"- **Canonical Metadata Payload**:\n")
                    f.write(f"```json\n{json.dumps(item.get('metadata'), indent=2)}\n```\n\n")
            else:
                f.write("No understood signals found.\n")
                
        print(f"Report written to {report_path}")
    print("Execution complete.")

if __name__ == "__main__":
    main()
