# src/agents/daily_brief/llm_renderer.py

import json
from loguru import logger
from intelligence.routing.router import IntelligenceRouter
from configs.constants import TaskType

class DailyBriefLLMRenderer:
    """
    Renders daily intelligence briefs using the LLM.
    """

    @staticmethod
    def render_brief(context: dict, brief_type: str) -> str:
        logger.info(f"DailyBriefLLMRenderer: Formatting prompt for {brief_type} brief...")

        # Construct prompt
        prompt = f"""You are Jarvis, a personal AI operating system.
Generate a premium, clean, and highly readable daily summary briefing in Markdown for the user based on the following structured life context.

### User Life Context Data (JSON):
{json.dumps(context, indent=2)}

### Briefing Type:
{brief_type}

### Content Guidelines & Constraints:
- Output Markdown ONLY. No preamble, no conversational fillers, no motivational or sign-off/sign-on remarks.
- Write in a highly concise and actionable tone.
- Strict limit of 250 words maximum.
- Prioritize attention/action items first.
- Clearly reference overdue tasks (including count and top items) and upcoming events (within 7 days).
- List the top 3 priorities of the day.

### Formatting & Design Constraints:
- Structure it with clear, professional headers:
  - If MORNING: Use headers "## Priority Actions", "## Financial Snapshot", "## Important Updates", "## Family Updates", and "## Insights".
  - If EVENING: Use headers "## Completed Actions", "## Facts Learned", "## FYI Alerts Received".
- When listing tasks, use standard Markdown checkbox style (`- [ ]`) or bullet points (`-`).

Begin briefing:
"""
        try:
            router = IntelligenceRouter()
            response = router.ask(prompt, TaskType.SUMMARY)
            if not response or "Cloud reasoning unavailable" in response:
                raise ValueError("Cloud LLM routing failed or returned placeholder output.")
            return response
        except Exception as e:
            logger.error(f"Failed to generate brief via LLM: {e}. Falling back to deterministic brief.")
            # Conforms with SPRINT DB-01.7 Fallback Validation template
            lines = [
                "Daily Brief",
                "",
                f"Tasks Due Today: {len(context.get('today_tasks', []))}",
                f"Overdue Tasks: {context.get('overdue_task_count', 0)}",
                f"New Facts: {len(context.get('new_facts', []))}",
                f"Financial Events: {len(context.get('financial_activity', []))}"
            ]
            return "\n".join(lines)
