# services/daily_brief_agent.py

from src.agents.daily_brief.agent import DailyBriefAgent as CoreDailyBriefAgent


class DailyBriefAgent:
    """
    Facade wrapper for pipeline orchestrator compatibility.
    """

    @classmethod
    def generate_briefs(cls, db_session) -> dict:
        """
        Executes morning and evening brief generations.
        """
        morning_id = CoreDailyBriefAgent.generate_morning_brief(db_session)
        evening_id = CoreDailyBriefAgent.generate_evening_brief(db_session)
        return {
            "morning_brief_id": morning_id,
            "evening_brief_id": evening_id
        }
