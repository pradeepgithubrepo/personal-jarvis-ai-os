"""
src/intelligence/contracts/contract_schema.py

Canonical contract schema definition for Jarvis V2 Phase 2B.

The canonical contract is the ONLY interface between the Signal Understanding Agent (SUA)
and downstream agents (Financial, Todo, FYI, Fact).

No downstream agent may inspect raw signal text. They consume this contract exclusively.

Build Constitution: BC-5
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field

# Contract version constant — increment when schema changes (requires new CONTRACT_SCHEMA_VN.md)
CONTRACT_VERSION = 1


class SignalType(str, Enum):
    """Enumeration of all valid signal types produced by the SUA."""
    FINANCIAL = "FINANCIAL"
    ACTION = "ACTION"
    FYI = "FYI"
    FACT = "FACT"
    NOISE = "NOISE"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class ContractValidationError(Exception):
    """
    Raised when a contract fails validation.
    Invalid contracts must never be dispatched downstream.
    """
    def __init__(self, errors: list[str], contract: dict | None = None):
        self.errors = errors
        self.contract = contract
        super().__init__(f"Contract validation failed with {len(errors)} error(s): {'; '.join(errors)}")


@dataclass
class CanonicalContract:
    """
    The versioned canonical signal contract produced by the SUA.

    This is the authoritative data structure passed to all downstream agents.
    Agents must never receive or inspect the raw signal message.
    """
    # --- Core fields (all signal types) ---
    contract_version: int
    signal_type: str
    importance: float
    confidence: float
    summary: str
    entities: list[str] = field(default_factory=list)

    # --- Candidate flags ---
    memory_candidate: bool = False
    requires_action: bool = False
    financial_candidate: bool = False
    fact_candidate: bool = False
    fyi_candidate: bool = False
    noise_candidate: bool = False

    # --- Type-specific payload ---
    type_specific: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "CanonicalContract":
        """
        Construct a CanonicalContract from a raw dict (e.g., from contract_json column).
        Does NOT validate — call ContractValidator.validate() separately.
        """
        return cls(
            contract_version=data.get("contract_version", CONTRACT_VERSION),
            signal_type=data.get("signal_type", ""),
            importance=float(data.get("importance", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            summary=data.get("summary", ""),
            entities=data.get("entities", []),
            memory_candidate=bool(data.get("memory_candidate", False)),
            requires_action=bool(data.get("requires_action", False)),
            financial_candidate=bool(data.get("financial_candidate", False)),
            fact_candidate=bool(data.get("fact_candidate", False)),
            fyi_candidate=bool(data.get("fyi_candidate", False)),
            noise_candidate=bool(data.get("noise_candidate", False)),
            type_specific=data.get("type_specific", data.get("contract_json_inner", {})),
        )

    def to_dict(self) -> dict:
        return {
            "contract_version": self.contract_version,
            "signal_type": self.signal_type,
            "importance": self.importance,
            "confidence": self.confidence,
            "summary": self.summary,
            "entities": self.entities,
            "memory_candidate": self.memory_candidate,
            "requires_action": self.requires_action,
            "financial_candidate": self.financial_candidate,
            "fact_candidate": self.fact_candidate,
            "fyi_candidate": self.fyi_candidate,
            "noise_candidate": self.noise_candidate,
            "type_specific": self.type_specific,
        }
