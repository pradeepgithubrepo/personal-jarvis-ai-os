"""
src/intelligence/routing/router.py

Signal router for Jarvis V2 Phase 2B.

Accepts an understood_signal record, validates its contract, and resolves
the target agents deterministically using routing_rules.

This module is the SIGNAL routing layer — it is NOT the LLM task router
(intelligence/routing/router.py which routes local vs cloud LLM).

Build Constitution: BC-5, P-1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from loguru import logger

from src.intelligence.contracts.contract_validator import ContractValidator
from src.intelligence.contracts.contract_schema import ContractValidationError
from src.intelligence.routing.routing_rules import resolve_route


@dataclass
class RouteDecision:
    """
    The routing decision for a single understood signal.

    Produced by SignalRouter.route() and consumed by ContractDispatcher.
    """
    understood_signal_id: str
    signal_type: str
    route_to: list[str] = field(default_factory=list)
    contract: dict = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    is_valid: bool = True

    @property
    def has_routes(self) -> bool:
        return len(self.route_to) > 0


class SignalRouter:
    """
    Validates and routes understood signals to downstream agents.

    Input:  understood_signal dict (from Supabase understood_signals table)
    Output: RouteDecision with resolved agent list

    Routing is fully deterministic — no LLM involvement.
    """

    def route(self, understood_signal: dict) -> RouteDecision:
        """
        Validate the contract and resolve routing for an understood signal.

        Args:
            understood_signal: A row from understood_signals, including contract_json.

        Returns:
            RouteDecision with route_to list and validation state.
        """
        signal_id = str(understood_signal.get("id", "unknown"))
        signal_type = understood_signal.get("signal_type", "")

        # Extract contract — may be nested in contract_json or be the full understood_signal
        contract = understood_signal.get("contract_json", {})
        if not isinstance(contract, dict):
            contract = {}

        # Enrich contract with top-level fields if not already present
        # (SUA stores signal_type, importance, confidence at top level AND in contract_json)
        enriched_contract = self._enrich_contract(understood_signal, contract)

        # Validate contract
        validation_result = ContractValidator.validate(enriched_contract, signal_id=signal_id)

        if not validation_result.valid:
            logger.warning(
                f"Invalid contract for signal {signal_id} | "
                f"type={signal_type} | errors={validation_result.errors}"
            )
            return RouteDecision(
                understood_signal_id=signal_id,
                signal_type=signal_type,
                route_to=[],
                contract=enriched_contract,
                validation_errors=validation_result.errors,
                is_valid=False,
            )

        # Resolve routes deterministically
        route_to = resolve_route(signal_type, enriched_contract)

        logger.info(
            f"Routing signal {signal_id} | type={signal_type} | route_to={route_to}"
        )

        return RouteDecision(
            understood_signal_id=signal_id,
            signal_type=signal_type,
            route_to=route_to,
            contract=enriched_contract,
            validation_errors=[],
            is_valid=True,
        )

    def _enrich_contract(self, understood_signal: dict, contract: dict) -> dict:
        """
        Build the full enriched canonical contract.

        The SUA stores core fields (signal_type, importance, confidence, summary)
        at the top level of understood_signals. The contract_json holds type-specific
        and candidate flag fields. This method merges them into a single canonical dict.
        """
        from src.intelligence.contracts.contract_schema import CONTRACT_VERSION

        enriched = dict(contract)  # start from contract_json

        # Always set/override with top-level fields from understood_signal
        enriched["contract_version"] = contract.get("contract_version", CONTRACT_VERSION)
        enriched["signal_type"] = understood_signal.get("signal_type", contract.get("signal_type", ""))
        enriched["importance"] = understood_signal.get("importance", contract.get("importance", 0.0))
        enriched["confidence"] = understood_signal.get("confidence", contract.get("confidence", 0.0))
        enriched["summary"] = understood_signal.get("summary", contract.get("summary", ""))

        # Ensure standard fields have defaults
        enriched.setdefault("entities", [])
        enriched.setdefault("memory_candidate", False)
        enriched.setdefault("requires_action", False)
        enriched.setdefault("financial_candidate", False)
        enriched.setdefault("fact_candidate", False)
        enriched.setdefault("fyi_candidate", False)
        enriched.setdefault("noise_candidate", False)
        enriched.setdefault("type_specific", {})

        return enriched
