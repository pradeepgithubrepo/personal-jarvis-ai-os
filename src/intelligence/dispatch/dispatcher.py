"""
src/intelligence/dispatch/dispatcher.py

Contract dispatcher for Jarvis V2 Phase 2B.

Responsibilities:
- Accept a RouteDecision from SignalRouter
- Invoke each target agent in the route list
- Write a signal_routes audit row per agent (started_at, completed_at, status)
- Return aggregate DispatchResult
- Support single-route and multi-route
- Support future agents via dispatch_registry

All dispatched agents receive ONLY the canonical contract — never raw text.

Build Constitution: BC-5, AD-3 (signal_routes owned by Dispatcher)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.intelligence.routing.router import RouteDecision
from src.intelligence.dispatch.dispatch_registry import get_agent
from src.agents.stubs.base_agent_stub import AgentResult


@dataclass
class AgentDispatchRecord:
    """Outcome of dispatching to a single agent."""
    agent_name: str
    status: str           # DISPATCHED | COMPLETED | FAILED | SKIPPED
    started_at: str = ""
    completed_at: str = ""
    error_message: str = ""
    result: AgentResult | None = None


@dataclass
class DispatchResult:
    """Aggregate result of dispatching a signal to all routed agents."""
    understood_signal_id: str
    signal_type: str
    total_routes: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    records: list[AgentDispatchRecord] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        if self.validation_errors:
            return "VALIDATION_FAILED"
        if self.total_routes == 0:
            return "NO_ROUTE"  # NOISE signal
        if self.failed == 0:
            return "SUCCESS"
        if self.completed > 0:
            return "PARTIAL_SUCCESS"
        return "FAILED"


class ContractDispatcher:
    """
    Dispatches validated contracts to downstream agents and records the audit trail.

    Dispatch flow:
        RouteDecision → [validate] → [for each agent: invoke stub → write signal_routes row]
    """

    def dispatch(
        self,
        route_decision: RouteDecision,
        supabase_client: Any = None,
    ) -> DispatchResult:
        """
        Dispatch a validated route decision to target agents.

        Args:
            route_decision: The routing decision from SignalRouter.
            supabase_client: Optional Supabase client for audit trail writes.
                             If None, audit trail is logged only (no DB write).

        Returns:
            DispatchResult with per-agent status records.
        """
        signal_id = route_decision.understood_signal_id
        signal_type = route_decision.signal_type

        result = DispatchResult(
            understood_signal_id=signal_id,
            signal_type=signal_type,
            total_routes=len(route_decision.route_to),
            validation_errors=route_decision.validation_errors,
        )

        # Handle invalid contracts — write a VALIDATION_FAILED audit row
        if not route_decision.is_valid:
            logger.error(
                f"Dispatcher: contract invalid for signal {signal_id} | "
                f"errors={route_decision.validation_errors}"
            )
            self._write_route_audit(
                supabase_client=supabase_client,
                understood_signal_id=signal_id,
                agent_name="__validation__",
                route_status="VALIDATION_FAILED",
                started_at=_now(),
                completed_at=_now(),
                error_message="; ".join(route_decision.validation_errors),
            )
            return result

        # Handle NOISE (no routes) — nothing to dispatch
        if not route_decision.has_routes:
            logger.info(
                f"Dispatcher: NOISE signal {signal_id} — pipeline terminated, no dispatch"
            )
            return result

        # Dispatch to each agent
        for agent_name in route_decision.route_to:
            record = self._dispatch_to_agent(
                agent_name=agent_name,
                contract=route_decision.contract,
                signal_id=signal_id,
                supabase_client=supabase_client,
            )
            result.records.append(record)

            if record.status == "COMPLETED":
                result.completed += 1
            elif record.status == "FAILED":
                result.failed += 1
            else:
                result.skipped += 1

        logger.info(
            f"Dispatcher: signal {signal_id} dispatch complete | "
            f"status={result.overall_status} | "
            f"completed={result.completed}/{result.total_routes}"
        )

        return result

    def _dispatch_to_agent(
        self,
        agent_name: str,
        contract: dict,
        signal_id: str,
        supabase_client: Any,
    ) -> AgentDispatchRecord:
        """Dispatch contract to a single agent and record the outcome."""
        started_at = _now()

        agent = get_agent(agent_name)

        if agent is None:
            completed_at = _now()
            error = f"Agent '{agent_name}' not found in registry"
            logger.error(f"Dispatcher: {error} | signal={signal_id}")
            self._write_route_audit(
                supabase_client=supabase_client,
                understood_signal_id=signal_id,
                agent_name=agent_name,
                route_status="FAILED",
                started_at=started_at,
                completed_at=completed_at,
                error_message=error,
            )
            return AgentDispatchRecord(
                agent_name=agent_name,
                status="FAILED",
                started_at=started_at,
                completed_at=completed_at,
                error_message=error,
            )

        # Write DISPATCHED audit row before invoking
        self._write_route_audit(
            supabase_client=supabase_client,
            understood_signal_id=signal_id,
            agent_name=agent_name,
            route_status="DISPATCHED",
            started_at=started_at,
        )

        try:
            agent_result = agent.process(contract)
            completed_at = _now()

            # Update audit row to COMPLETED
            self._write_route_audit(
                supabase_client=supabase_client,
                understood_signal_id=signal_id,
                agent_name=agent_name,
                route_status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
            )

            logger.info(
                f"Dispatcher: {agent_name} completed | signal={signal_id} | "
                f"agent_status={agent_result.status}"
            )

            return AgentDispatchRecord(
                agent_name=agent_name,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                result=agent_result,
            )

        except Exception as e:
            completed_at = _now()
            error = str(e)
            logger.error(
                f"Dispatcher: {agent_name} FAILED | signal={signal_id} | error={error}"
            )

            self._write_route_audit(
                supabase_client=supabase_client,
                understood_signal_id=signal_id,
                agent_name=agent_name,
                route_status="FAILED",
                started_at=started_at,
                completed_at=completed_at,
                error_message=error,
            )

            return AgentDispatchRecord(
                agent_name=agent_name,
                status="FAILED",
                started_at=started_at,
                completed_at=completed_at,
                error_message=error,
            )

    def _write_route_audit(
        self,
        supabase_client: Any,
        understood_signal_id: str,
        agent_name: str,
        route_status: str,
        started_at: str,
        completed_at: str = None,
        error_message: str = None,
    ) -> None:
        """Write a signal_routes audit row to Supabase."""
        row = {
            "id": str(uuid.uuid4()),
            "understood_signal_id": understood_signal_id,
            "agent_name": agent_name,
            "route_status": route_status,
            "started_at": started_at,
            "created_at": started_at,
        }
        if completed_at:
            row["completed_at"] = completed_at
        if error_message:
            row["error_message"] = error_message[:1000]  # cap length

        if supabase_client is None:
            logger.debug(
                f"[no-db] signal_routes | signal={understood_signal_id} | "
                f"agent={agent_name} | status={route_status}"
            )
            return

        try:
            supabase_client.table("signal_routes").insert(row).execute()
        except Exception as e:
            # Audit write failure must not crash the dispatch — log and continue
            logger.error(
                f"Failed to write signal_routes audit | "
                f"signal={understood_signal_id} | agent={agent_name} | error={e}"
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
