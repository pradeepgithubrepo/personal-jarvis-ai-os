# verify_daily_brief_llm.py
import sys
import os
import json
from loguru import logger
import dotenv

# Load env variables
dotenv.load_dotenv("/home/prad/petprojects/ai/jarvis/.env")

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from configs.settings import settings
from configs.constants import TaskType
from src.agents.daily_brief.llm_renderer import DailyBriefLLMRenderer

def test_llm_routing_diagnostics():
    logger.info("=========================================")
    logger.info("Daily Brief LLM Route Diagnostic Tool")
    logger.info("=========================================")
    
    # 1. Build sample DailyBriefContext
    sample_context = {
        "target_date": "2026-07-01",
        "overdue_task_count": 2,
        "overdue_tasks": [
            {"todo_id": "1", "title": "Overdue task 1", "priority": "HIGH"},
            {"todo_id": "2", "title": "Overdue task 2", "priority": "MEDIUM"}
        ],
        "today_tasks": [
            {"todo_id": "3", "title": "Today task 1", "priority": "CRITICAL"}
        ],
        "upcoming_events": [
            {"todo_id": "4", "title": "Upcoming task 1", "due_date": "2026-07-04"}
        ],
        "new_facts": [],
        "new_fyis": [],
        "financial_activity": [],
        "financial_summary": {
            "yesterday_spend": 0.0,
            "biggest_expense": None,
            "spending_category_summary": {}
        },
        "top_priorities": []
    }

    # 2. Retrieve configs
    selected_provider = settings.cloud_provider
    selected_model = os.environ.get("LOCAL_MODEL", "qwen2.5:1.5b")
    
    logger.info(f"Target cloud provider in settings: {selected_provider}")
    logger.info(f"Target local model in env: {selected_model}")
    logger.info("Environment Keys Check:")
    logger.info(f"GEMINI_API_KEY present: {'GEMINI_API_KEY' in os.environ}")
    logger.info(f"OPENAI_API_KEY present: {'OPENAI_API_KEY' in os.environ}")
    
    # 3. Call renderer (with custom prints)
    logger.info("Executing LLM generation path...")
    
    # Construct mock prompt for size check
    prompt_draft = f"Life Context: {json.dumps(sample_context)}"
    logger.info(f"Prompt length (approx characters): {len(prompt_draft)}")
    
    try:
        from intelligence.routing.router import IntelligenceRouter
        router = IntelligenceRouter()
        
        # Test routing and provider directly to get raw response before renderer's fallback
        logger.info(f"Routing task '{TaskType.SUMMARY}' via IntelligenceRouter.ask...")
        raw_response = router.ask(prompt_draft, TaskType.SUMMARY)
        logger.success(f"Raw provider response payload:\n{raw_response}")
        
    except Exception as e:
        logger.error(f"Routing failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_routing_diagnostics()
