# services/fyi_agent.py

from src.agents.fyi.agent import FyiAgent as CoreFyiAgent


class FyiAgent:
    """
    Facade wrapper for pipeline orchestrator compatibility.
    """

    @classmethod
    def process_all_understood_signals(cls, db_session) -> dict:
        return CoreFyiAgent.process_all_understood_signals(db_session)
