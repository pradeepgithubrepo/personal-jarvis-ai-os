"""
src/agents/stubs/fyi_agent_stub.py

FYI Agent stub — Phase 2B placeholder.

The real FYI Agent will be implemented in Phase 3C.
"""
from loguru import logger
from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult


class FyiAgentStub(BaseAgentStub):
    """
    Stub implementation of the FYI Agent.

    Accepts FYI contracts, logs them, returns STUB_ACCEPTED.
    Does not write to fyi_events table.
    Real implementation: Phase 3C — FYI Agent Foundation.
    """

    @property
    def agent_name(self) -> str:
        return "fyi_agent"

    def process(self, contract: dict) -> AgentResult:
        signal_type = contract.get("signal_type", "UNKNOWN")
        summary = contract.get("summary", "")
        event_name = contract.get("type_specific", {}).get("event_name", summary)
        event_time = contract.get("type_specific", {}).get("event_time")

        logger.info(
            f"[STUB] fyi_agent received contract | "
            f"type={signal_type} | event={event_name!r} | time={event_time}"
        )

        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="FYI Agent stub accepted contract. Awaiting Phase 3C implementation.",
            output={
                "event_name": event_name,
                "event_time": event_time,
            },
        )
