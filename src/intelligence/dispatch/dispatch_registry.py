"""
src/intelligence/dispatch/dispatch_registry.py

Agent dispatch registry for Jarvis V2 Phase 2B.

Maps agent name strings to their stub (or real) instances.
The dispatcher resolves agents from this registry.

To add a new agent in Phase 3+:
  1. Create the real agent class
  2. Register it here (replacing the stub)
  3. Delete the stub (Build Constitution BC-2)
"""
from __future__ import annotations

from loguru import logger

from src.agents.stubs.base_agent_stub import BaseAgentStub
from src.agents.stubs.financial_agent_stub import FinancialAgentStub
from src.agents.stubs.todo_agent_stub import TodoAgentStub
from src.agents.stubs.fyi_agent_stub import FyiAgentStub
from src.agents.stubs.fact_agent_stub import FactAgentStub


# ---------------------------------------------------------------------------
# Agent Registry
# Maps canonical agent name → agent instance
# Phase 2B: all entries point to stubs
# Phase 3+: replace stub instances with real agent instances
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, BaseAgentStub] = {
    "financial_agent": FinancialAgentStub(),
    "todo_agent":      TodoAgentStub(),
    "fyi_agent":       FyiAgentStub(),
    "fact_agent":      FactAgentStub(),
}


def get_agent(agent_name: str) -> BaseAgentStub | None:
    """
    Resolve an agent by name.

    Returns None if agent is not registered.
    """
    agent = _REGISTRY.get(agent_name)
    if agent is None:
        logger.warning(f"Agent not found in registry: {agent_name!r}")
    return agent


def list_agents() -> list[str]:
    """Return list of all registered agent names."""
    return list(_REGISTRY.keys())


def register_agent(agent_name: str, agent: BaseAgentStub) -> None:
    """
    Register or replace an agent in the registry.

    Used in Phase 3+ when real agents replace stubs.
    """
    logger.info(f"Registering agent: {agent_name!r} → {type(agent).__name__}")
    _REGISTRY[agent_name] = agent
