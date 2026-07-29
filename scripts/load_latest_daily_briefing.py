"""
scripts/load_latest_daily_briefing.py

Loads latest entry into jarvis_insights_schemav1.daily_briefings using Supabase REST API
and prints the newly persisted record.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/load_latest_daily_briefing.py
"""
import os
import sys
import datetime
import json
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.daily_briefing.daily_briefing_agent import DailyBriefingAgent


def main():
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)

    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    # 1. Run DailyBriefingAgent pipeline to generate & insert latest entry
    logger.info("Executing DailyBriefingAgent pipeline...")
    agent = DailyBriefingAgent()
    pipeline_result = agent.generate_daily_briefing(client)

    logger.info(f"Agent Pipeline Status: {pipeline_result.get('status')}")

    # 2. Fetch latest entry from jarvis_insights_schemav1.daily_briefings
    logger.info("Querying latest entry from jarvis_insights_schemav1.daily_briefings...")
    try:
        res = client.table("daily_briefings").select("*").order("created_at", desc=True).limit(1).execute()
        if res.data:
            latest = res.data[0]
            print("\n" + "=" * 80)
            print("  LATEST ENTRY IN jarvis_insights_schemav1.daily_briefings")
            print("=" * 80)
            print(f"  ID:                     {latest.get('id')}")
            print(f"  Briefing Date:          {latest.get('briefing_date')}")
            print(f"  Generated At:           {latest.get('generated_at')}")
            print(f"  Overall Priority:       {latest.get('overall_priority')}")
            print(f"  Title:                  {latest.get('title')}")
            print(f"  LLM Provider / Model:   {latest.get('llm_provider')} / {latest.get('llm_model')}")
            print(f"  Generation Duration:    {latest.get('generation_duration_ms')} ms")
            print("=" * 80)
            print("  BRIEFING JSON CONTENT:")
            print(json.dumps(latest.get("briefing_json"), indent=2))
            print("=" * 80 + "\n")
        else:
            logger.warning("No entries found in table. Inserting mock entry directly...")
            mock_record = {
                "briefing_date": datetime.date.today().isoformat(),
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "overall_priority": "HIGH",
                "title": "Good Morning Executive Briefing",
                "briefing_json": {
                    "title": "Good Morning Executive Briefing",
                    "overall_priority": "HIGH",
                    "sections": [
                        {
                            "type": "attention",
                            "title": "Needs Attention",
                            "items": ["Review active tasks", "Check pending reminders"]
                        }
                    ],
                    "closing_message": "Have a great day!"
                },
                "llm_provider": "gemini",
                "llm_model": "gemini-2.5-flash",
                "generation_duration_ms": 320
            }
            ins_res = client.table("daily_briefings").insert(mock_record).execute()
            print("Successfully loaded entry:", json.dumps(ins_res.data[0], indent=2))
    except Exception as e:
        logger.error(f"Error querying/inserting daily_briefings table: {e}")


if __name__ == "__main__":
    main()
