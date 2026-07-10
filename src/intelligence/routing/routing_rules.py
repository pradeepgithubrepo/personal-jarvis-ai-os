"""
src/intelligence/routing/routing_rules.py

Deterministic routing rules for Jarvis V2 Phase 2B.

These rules are the sole authority for which downstream agents receive
a given signal. Rules are pure data — no LLM involvement.

Build Constitution: BC-5, P-1 (LLMs Interpret. Agents Own Business Logic.)
"""
from __future__ import annotations

from src.intelligence.contracts.contract_schema import SignalType


# ---------------------------------------------------------------------------
# Primary routing table
# Maps signal_type → list of agents to dispatch (order matters for audit trail)
# ---------------------------------------------------------------------------
PRIMARY_ROUTING_TABLE: dict[str, list[str]] = {
    SignalType.FINANCIAL: ["financial_agent"],
    SignalType.ACTION:    ["todo_agent"],
    SignalType.FYI:       ["fyi_agent"],
    SignalType.FACT:      ["fact_agent"],
    SignalType.NOISE:     [],  # Terminate pipeline. No dispatch.
}


# ---------------------------------------------------------------------------
# Conditional routing rules
# Applied AFTER primary routing when contract flags trigger additional routes
# ---------------------------------------------------------------------------
CONDITIONAL_ROUTES: list[dict] = [
    {
        # FINANCIAL + memory_candidate=True → also dispatch to fact_agent
        "condition_signal_types": [SignalType.FINANCIAL],
        "condition_flag": "memory_candidate",
        "condition_value": True,
        "additional_agents": ["fact_agent"],
    },
    {
        # ACTION + memory_candidate=True → also dispatch to fact_agent
        "condition_signal_types": [SignalType.ACTION],
        "condition_flag": "memory_candidate",
        "condition_value": True,
        "additional_agents": ["fact_agent"],
    },
]


def resolve_route(signal_type: str, contract: dict) -> list[str]:
    """
    Resolve the full list of target agents for a given signal_type and contract.

    This is a pure function — deterministic, no side effects, no LLM.

    Args:
        signal_type: The classified signal type (e.g., "FINANCIAL").
        contract: The full canonical contract dict (including candidate flags).

    Returns:
        List of agent names to dispatch to. Empty list = pipeline terminates (NOISE).
    """
    # Start with primary route
    agents: list[str] = list(PRIMARY_ROUTING_TABLE.get(signal_type, []))

    # Apply conditional routes
    for rule in CONDITIONAL_ROUTES:
        if signal_type not in rule["condition_signal_types"]:
            continue

        flag_value = contract.get(rule["condition_flag"], False)
        if flag_value == rule["condition_value"]:
            for agent in rule["additional_agents"]:
                if agent not in agents:
                    agents.append(agent)

    return agents
