"""
src/agents/stubs/base_agent_stub.py

Abstract base class for all downstream agent stubs.

Phase 2B creates stubs only — these are interface placeholders.
Real implementations are built in Phase 3A (Financial), Phase 3B (Todo),
Phase 3C (FYI), Phase 3D (Fact).

Design principle: BC-5 — Downstream agents consume canonical contracts only.
They never receive raw signal text.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentResult:
    """Result returned by an agent stub after processing a contract."""
    agent_name: str
    status: str          # "STUB_ACCEPTED" | "STUB_REJECTED" | "COMPLETED" | "FAILED"
    message: str = ""
    output: dict = None

    def __post_init__(self):
        if self.output is None:
            self.output = {}


class BaseAgentStub(ABC):
    """
    Abstract base class for all downstream agent stubs.

    All concrete stubs must implement `process()`. When real agents replace stubs
    in Phase 3+, they subclass this and implement the full business logic.
    """

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """The unique registered name of this agent."""
        ...

    @abstractmethod
    def process(self, contract: dict) -> AgentResult:
        """
        Process a canonical contract.

        Args:
            contract: The full enriched canonical contract dict.
                      Must NOT contain raw signal text — only contract fields.

        Returns:
            AgentResult with processing status and any output data.
        """
        ...
