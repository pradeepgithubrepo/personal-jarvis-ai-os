"""
src/agents/stubs/fact_agent_stub.py

Fact Agent stub — Phase 2B placeholder.

The real Fact Agent will be implemented in Phase 3D.
"""
from loguru import logger
from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult


class FactAgentStub(BaseAgentStub):
    """
    Stub implementation of the Fact Agent.

    Accepts FACT contracts AND contracts with memory_candidate=True
    (from FINANCIAL or ACTION signals that also dispatch to fact_agent).
    Does not write to facts table.
    Real implementation: Phase 3D — Fact Agent Foundation.
    """

    @property
    def agent_name(self) -> str:
        return "fact_agent"

    def process(self, contract: dict) -> AgentResult:
        signal_type = contract.get("signal_type", "UNKNOWN")
        summary = contract.get("summary", "")
        memory_candidate = contract.get("memory_candidate", False)
        entity = contract.get("type_specific", {}).get("entity")
        attribute = contract.get("type_specific", {}).get("attribute")
        value = contract.get("type_specific", {}).get("value")

        logger.info(
            f"[STUB] fact_agent received contract | "
            f"type={signal_type} | memory_candidate={memory_candidate} | "
            f"entity={entity!r} | attr={attribute!r} | value={value!r} | "
            f"summary={summary!r}"
        )

        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="Fact Agent stub accepted contract. Awaiting Phase 3D implementation.",
            output={
                "entity": entity,
                "attribute": attribute,
                "value": value,
                "memory_candidate": memory_candidate,
            },
        )
