"""
scripts/run_master_daily_pipeline.py

Master Daily Pipeline Orchestrator — End-to-End Execution Engine.

Links all 9 pipeline processing stages so that every execution automatically completes
the full flow from raw signal ingestion to executive daily briefing generation:

  1. Consumer Signal Ingestion   (Supabase Storage incoming/ -> mobile_signals)
  2. Qualification Agent V2     (mobile_signals -> qualified_signals)
  3. Signal Understanding (SUA) (qualified_signals -> understood_signals)
  4. Router & Dispatcher         (understood_signals -> signal_routes)
  5. To-Do Agent Ingestion       (signal_routes -> tasks)
  6. FYI / Information Agent     (signal_routes -> information_items)
  7. Financial Agent & Rollups   (financial_transactions & monthly summaries)
  8. Lifecycle Agent Engine      (ACTIVE items -> tasks / rescheduling)
  9. Daily Briefing Agent        (Generates 10/10 Executive Briefing -> daily_briefings)

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_master_daily_pipeline.py --trigger SCHEDULED
"""
import os
import sys
import uuid
import json
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.consumer.orchestrator import run_pipeline as run_consumer_pipeline
from src.agents.consumer.qualification_agent import SignalQualificationAgent
from src.agents.sua.orchestrator import run_pipeline as run_sua_pipeline
from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher
from src.agents.todo.todo_agent import TodoAgent
from src.agents.fyi.fyi_agent import FyiAgent
from src.agents.financial.financial_agent import FinancialAgent
from src.agents.lifecycle.lifecycle_agent import LifecycleAgent
from src.agents.daily_briefing.daily_briefing_agent import DailyBriefingAgent


def run_master_pipeline(client: Client, trigger_type: str = "SCHEDULED") -> dict:
    started_at = datetime.now(timezone.utc)
    run_id = uuid.uuid4()

    logger.info(f"=== STARTING MASTER DAILY PIPELINE (Run ID: {run_id} | Trigger: {trigger_type}) ===")

    # Track pipeline run in DB
    try:
        run_row = {
            "run_id": str(run_id),
            "pipeline_name": "master_daily_pipeline",
            "phase": "end_to_end_v2",
            "trigger_type": trigger_type,
            "started_at": started_at.isoformat(),
            "status": "STARTED",
            "host_name": "JarvisMasterPipeline",
            "user_name": "prad",
            "version": "v2.2.0-master",
            "metadata": {"trigger": trigger_type}
        }
        client.table("pipeline_runs").insert(run_row).execute()
    except Exception as e:
        logger.warning(f"master_pipeline: Could not insert pipeline_runs record: {e}")

    stage_results = {}

    # Stage 1: Consumer Signal Ingestion
    logger.info("\n--- Stage 1: Consumer Signal Ingestion ---")
    try:
        res_consumer = run_consumer_pipeline(client, trigger_type=trigger_type)
        stage_results["stage1_consumer"] = res_consumer
        logger.info(f"✓ Stage 1 Complete: {res_consumer.get('signals_created', 0)} signals created from {res_consumer.get('files_processed', 0)} files.")
    except Exception as e:
        logger.error(f"✗ Stage 1 Consumer Failed: {e}")
        stage_results["stage1_consumer"] = {"status": "FAILED", "error": str(e)}

    # Stage 2: Qualification Agent V2
    logger.info("\n--- Stage 2: Qualification Agent V2 ---")
    try:
        res_unproc = client.table("mobile_signals").select("*").eq("processed", False).order("id").execute()
        unprocessed_signals = res_unproc.data or []
        logger.info(f"Found {len(unprocessed_signals)} unprocessed signals in mobile_signals.")

        if unprocessed_signals:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config")
            qual_agent = SignalQualificationAgent(config_dir=config_path)
            qualified_inserts = []
            mobile_signal_updates = []

            for sig in unprocessed_signals:
                outcome = qual_agent.qualify_signal(sig)
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

            # Bulk insert qualified_signals
            chunk_size = 100
            for i in range(0, len(qualified_inserts), chunk_size):
                client.table("qualified_signals").insert(qualified_inserts[i:i + chunk_size]).execute()

            # Bulk update processed flag
            for i in range(0, len(mobile_signal_updates), chunk_size):
                client.table("mobile_signals").update({"processed": True}).in_("id", mobile_signal_updates[i:i + chunk_size]).execute()

            stage_results["stage2_qualification"] = {"status": "SUCCESS", "processed_count": len(unprocessed_signals), "qualified_count": len(qualified_inserts)}
            logger.info(f"✓ Stage 2 Complete: Qualified {len(qualified_inserts)} signals.")
        else:
            stage_results["stage2_qualification"] = {"status": "SUCCESS", "processed_count": 0}
            logger.info("✓ Stage 2 Complete: No unprocessed signals to qualify.")
    except Exception as e:
        logger.error(f"✗ Stage 2 Qualification Failed: {e}")
        stage_results["stage2_qualification"] = {"status": "FAILED", "error": str(e)}

    # Stage 3: Signal Understanding Agent (SUA)
    logger.info("\n--- Stage 3: Signal Understanding Agent (SUA) ---")
    try:
        res_sua = run_sua_pipeline(client, trigger_type=trigger_type, model_name="qwen2.5:1.5b")
        stage_results["stage3_sua"] = res_sua
        logger.info(f"✓ Stage 3 Complete: Understood {res_sua.get('signals_understood', 0)} signals.")
    except Exception as e:
        logger.error(f"✗ Stage 3 SUA Failed: {e}")
        stage_results["stage3_sua"] = {"status": "FAILED", "error": str(e)}

    # Stage 4: Signal Router & Dispatcher
    logger.info("\n--- Stage 4: Signal Router & Dispatcher ---")
    try:
        # Only query understood signals that have not been routed yet
        res_us = client.table("understood_signals").select("*, signal_routes(id)").execute()
        all_signals = res_us.data or []
        understood_signals = [
            us for us in all_signals
            if not us.get("signal_routes")
        ]
        logger.info(f"Routing {len(understood_signals)} unprocessed understood signals (out of {len(all_signals)} total)...")

        router = SignalRouter()
        dispatcher = ContractDispatcher()
        routed_cnt = 0

        for us in understood_signals:
            decision = router.route(us)
            dispatcher.dispatch(decision, client)
            routed_cnt += 1

        stage_results["stage4_routing"] = {"status": "SUCCESS", "routed_count": routed_cnt}
        logger.info(f"✓ Stage 4 Complete: Routed {routed_cnt} signals.")
    except Exception as e:
        logger.error(f"✗ Stage 4 Routing Failed: {e}")
        stage_results["stage4_routing"] = {"status": "FAILED", "error": str(e)}

    # Stage 5: To-Do Agent Ingestion Worker
    logger.info("\n--- Stage 5: To-Do Agent Ingestion Worker ---")
    try:
        todo_agent = TodoAgent()
        todo_agent.process_pending_routes(client)
        stage_results["stage5_todo"] = {"status": "SUCCESS"}
        logger.info("✓ Stage 5 Complete: To-Do Agent processed pending routes.")
    except Exception as e:
        logger.error(f"✗ Stage 5 To-Do Agent Failed: {e}")
        stage_results["stage5_todo"] = {"status": "FAILED", "error": str(e)}

    # Stage 5b: FYI / Information Agent Ingestion Worker
    logger.info("\n--- Stage 5b: FYI Agent Ingestion Worker ---")
    try:
        fyi_agent = FyiAgent()
        fyi_agent.process_pending_routes(client)
        stage_results["stage5b_fyi"] = {"status": "SUCCESS"}
        logger.info("✓ Stage 5b Complete: FYI Agent processed pending routes.")
    except Exception as e:
        logger.error(f"✗ Stage 5b FYI Agent Failed: {e}")
        stage_results["stage5b_fyi"] = {"status": "FAILED", "error": str(e)}

    # Stage 5c: Financial Agent Ingestion Worker
    logger.info("\n--- Stage 5c: Financial Agent Ingestion Worker ---")
    try:
        financial_agent = FinancialAgent()
        financial_agent.process_pending_routes(client)
        stage_results["stage5c_financial"] = {"status": "SUCCESS"}
        logger.info("✓ Stage 5c Complete: Financial Agent processed pending routes.")
    except Exception as e:
        logger.error(f"✗ Stage 5c Financial Agent Failed: {e}")
        stage_results["stage5c_financial"] = {"status": "FAILED", "error": str(e)}

    # Stage 6: Lifecycle Agent Engine
    logger.info("\n--- Stage 6: Lifecycle Agent Engine ---")
    try:
        lifecycle_agent = LifecycleAgent()
        res_life = lifecycle_agent.process_active_items(client)
        stage_results["stage6_lifecycle"] = res_life
        logger.info(f"✓ Stage 6 Complete: Promoted {res_life.get('promoted_count', 0)} lifecycle items.")
    except Exception as e:
        logger.error(f"✗ Stage 6 Lifecycle Agent Failed: {e}")
        stage_results["stage6_lifecycle"] = {"status": "FAILED", "error": str(e)}

    # Stage 7: Daily Briefing Agent (10/10 Executive Assistant)
    logger.info("\n--- Stage 7: Daily Briefing Agent (10/10 Signature Experience) ---")
    try:
        briefing_agent = DailyBriefingAgent()
        res_briefing = briefing_agent.generate_daily_briefing(client)
        stage_results["stage7_briefing"] = res_briefing
        logger.info(f"✓ Stage 7 Complete: Executive briefing generated (Status: {res_briefing.get('status')}).")
    except Exception as e:
        logger.error(f"✗ Stage 7 Daily Briefing Agent Failed: {e}")
        stage_results["stage7_briefing"] = {"status": "FAILED", "error": str(e)}

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    # Determine overall pipeline status
    failed_stages = [k for k, v in stage_results.items() if isinstance(v, dict) and v.get("status") == "FAILED"]
    overall_status = "SUCCESS" if not failed_stages else ("PARTIAL_SUCCESS" if len(failed_stages) < len(stage_results) else "FAILED")

    master_summary = {
        "run_id": str(run_id),
        "status": overall_status,
        "duration_ms": duration_ms,
        "failed_stages": failed_stages,
        "stage_results": stage_results,
    }

    # Update pipeline run status in DB
    try:
        client.table("pipeline_runs").update({
            "status": overall_status,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "metadata": {"summary": master_summary}
        }).eq("run_id", str(run_id)).execute()
    except Exception:
        pass

    logger.info(f"\n=== MASTER DAILY PIPELINE COMPLETE (Status: {overall_status} | Duration: {duration_ms} ms) ===")
    return master_summary


def main():
    parser = argparse.ArgumentParser(description="Jarvis Master Daily Pipeline Orchestrator CLI")
    parser.add_argument(
        "--trigger",
        choices=["MANUAL", "SCHEDULED", "RETRY", "RECOVERY"],
        default="SCHEDULED",
        help="Pipeline trigger type (default: SCHEDULED)"
    )
    args = parser.parse_args()

    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)

    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    summary = run_master_pipeline(client, trigger_type=args.trigger)

    print("\n" + "=" * 80)
    print("  MASTER DAILY PIPELINE RUN SUMMARY")
    print("=" * 80)
    print(f"  Run ID:      {summary.get('run_id')}")
    print(f"  Status:      {summary.get('status')}")
    print(f"  Duration:    {summary.get('duration_ms')} ms")
    print(f"  Failed:      {summary.get('failed_stages')}")
    print("=" * 80 + "\n")

    if summary.get("status") == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
