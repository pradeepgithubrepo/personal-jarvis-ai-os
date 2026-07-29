"""src/agents/stubs/__init__.py — Agent stub package for Phase 2B."""
from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult
from src.agents.stubs.financial_agent_stub import FinancialAgentStub
from src.agents.stubs.todo_agent_stub import TodoAgentStub
from src.agents.stubs.fyi_agent_stub import FyiAgentStub

__all__ = [
    "BaseAgentStub", "AgentResult",
    "FinancialAgentStub", "TodoAgentStub", "FyiAgentStub",
]
