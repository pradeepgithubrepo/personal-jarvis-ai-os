"""
src/agents/stubs/financial_agent_stub.py

Financial Agent stub — Phase 2B placeholder.

The real Financial Agent will be implemented in Phase 3A.
This stub accepts contracts and logs them without performing business logic.

When replaced in Phase 3A, this stub is deleted (Build Constitution BC-2).
"""
from loguru import logger
from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult


class FinancialAgentStub(BaseAgentStub):
    """
    Stub implementation of the Financial Agent.

    Accepts FINANCIAL contracts, logs the received data, and returns STUB_ACCEPTED.
    Does not write to financial_events or financial_facts tables.
    Real implementation: Phase 3A — Financial Agent Foundation.
    """

    @property
    def agent_name(self) -> str:
        return "financial_agent"

    def process(self, contract: dict) -> AgentResult:
        signal_type = contract.get("signal_type", "UNKNOWN")
        summary = contract.get("summary", "")
        amount = contract.get("type_specific", {}).get("amount")
        currency = contract.get("type_specific", {}).get("currency", "INR")
        tx_type = contract.get("type_specific", {}).get("transaction_type", "UNKNOWN")

        logger.info(
            f"[STUB] financial_agent received contract | "
            f"type={signal_type} | tx_type={tx_type} | "
            f"amount={currency} {amount} | summary={summary!r}"
        )

        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="Financial Agent stub accepted contract. Awaiting Phase 3A implementation.",
            output={
                "signal_type": signal_type,
                "amount": amount,
                "transaction_type": tx_type,
            },
        )
