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
    SignalType.NOISE:     [],  # Terminate pipeline. No dispatch.
}



# ---------------------------------------------------------------------------
# Conditional routing rules
# Applied AFTER primary routing when contract flags trigger additional routes
# ---------------------------------------------------------------------------
CONDITIONAL_ROUTES: list[dict] = [
    {
        # FINANCIAL + memory_candidate=True → also dispatch to fyi_agent
        "condition_signal_types": [SignalType.FINANCIAL],
        "condition_flag": "memory_candidate",
        "condition_value": True,
        "additional_agents": ["fyi_agent"],
    },
    {
        # ACTION + memory_candidate=True → also dispatch to fyi_agent
        "condition_signal_types": [SignalType.ACTION],
        "condition_flag": "memory_candidate",
        "condition_value": True,
        "additional_agents": ["fyi_agent"],
    },
]


def resolve_route(signal_type: str, contract: dict) -> tuple[list[str], str]:
    """
    Resolve the full list of target agents for a given signal_type and contract.

    This is a pure function — deterministic, no side effects, no LLM.

    Args:
        signal_type: The classified signal type (e.g., "FINANCIAL").
        contract: The full canonical contract dict (including candidate flags).

    Returns:
        Tuple of:
          - List of agent names to dispatch to. Empty list = pipeline terminates (NOISE).
          - String detailing the reason/logic for the resolved routes.
    """
    # Start with primary route
    agents: list[str] = list(PRIMARY_ROUTING_TABLE.get(signal_type, []))
    reasons: list[str] = []

    if agents:
        reasons.append(f"Primary route matched for {signal_type} -> {agents}")
    else:
        reasons.append(f"No primary route mapped for {signal_type}")

    # V2.2 Conditional: Action Flag Safety Route
    if contract.get("requires_action") is True or signal_type == SignalType.ACTION:
        if "todo_agent" not in agents:
            agents.append("todo_agent")
            reasons.append("Action safety rule triggered: contract.requires_action is True")

    # Apply other conditional routes
    for rule in CONDITIONAL_ROUTES:
        if signal_type not in rule["condition_signal_types"]:
            continue

        flag_value = contract.get(rule["condition_flag"], False)
        if flag_value == rule["condition_value"]:
            for agent in rule["additional_agents"]:
                if agent not in agents:
                    agents.append(agent)
                    reasons.append(f"Conditional rule triggered ({rule['condition_flag']}): added {agent}")

    return agents, "; ".join(reasons)
