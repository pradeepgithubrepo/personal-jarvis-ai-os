"""
src/agents/stubs/todo_agent_stub.py

Todo Agent stub — Phase 2B placeholder.

The real Todo Agent will be implemented in Phase 3B.
"""
from loguru import logger
from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult


class TodoAgentStub(BaseAgentStub):
    """
    Stub implementation of the Todo Agent.

    Accepts ACTION contracts, logs them, returns STUB_ACCEPTED.
    Does not write to todo_items table.
    Real implementation: Phase 3B — Todo Agent Foundation.
    """

    @property
    def agent_name(self) -> str:
        return "todo_agent"

    def process(self, contract: dict) -> AgentResult:
        signal_type = contract.get("signal_type", "UNKNOWN")
        summary = contract.get("summary", "")
        task_name = contract.get("type_specific", {}).get("task_name", summary)
        due_date = contract.get("type_specific", {}).get("due_date")

        logger.info(
            f"[STUB] todo_agent received contract | "
            f"type={signal_type} | task={task_name!r} | due={due_date}"
        )

        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="Todo Agent stub accepted contract. Awaiting Phase 3B implementation.",
            output={
                "task_name": task_name,
                "due_date": due_date,
            },
        )
