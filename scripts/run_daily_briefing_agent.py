"""
scripts/run_daily_briefing_agent.py

Runner script for the Daily Briefing Agent V1.
Executes the final daily pipeline step at 06:00 AM.

Usage:
    PYTHONPATH=. .venv/bin/python3 scripts/run_daily_briefing_agent.py
"""
import os
import sys
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
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables not set.")
        sys.exit(1)

    logger.info("Connecting to Supabase (jarvis_insights_schemav1)...")
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)

    logger.info("Initializing Daily Briefing Agent...")
    agent = DailyBriefingAgent()

    logger.info("Running Daily Briefing pipeline...")
    result = agent.generate_daily_briefing(client)

    logger.info(f"Pipeline Result Status: {result.get('status')}")
    briefing = result.get("briefing_record", {}).get("briefing_json", {})
    logger.info("\n" + "=" * 50)
    logger.info(f"DAILY BRIEFING TITLE: {briefing.get('title')}")
    logger.info(f"OVERALL PRIORITY:     {briefing.get('overall_priority')}")
    logger.info(f"LLM PROVIDER:         {result.get('briefing_record', {}).get('llm_provider')} ({result.get('briefing_record', {}).get('llm_model')})")
    logger.info(f"GENERATION DURATION:  {result.get('briefing_record', {}).get('generation_duration_ms')} ms")
    logger.info("=" * 50)
    logger.info("BRIEFING JSON OUTPUT:")
    logger.info(json.dumps(briefing, indent=2))
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
