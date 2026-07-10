"""
src/intelligence/replay/replay_router.py

Replay framework for Jarvis V2 Phase 2B.

Capability: Replay routing for an understood signal by ID.

Does NOT re-run:
  - Consumer (signal ingestion)
  - Qualification Agent
  - Signal Understanding Agent (SUA)

Only re-dispatches the routing layer using the already-stored contract.

This enables:
  - Recovering from dispatch failures
  - Re-routing when routing rules change
  - Testing new agent implementations against historical contracts
  - Full audit trail (new signal_routes rows are written — old ones preserved)

Build Constitution: P-6 (Replayable Events)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher, DispatchResult


@dataclass
class ReplayResult:
    """Result of a replay operation."""
    understood_signal_id: str
    found: bool = False
    dispatch_result: DispatchResult | None = None
    error: str = ""

    @property
    def success(self) -> bool:
        return self.found and self.dispatch_result is not None and not self.error


class ReplayRouter:
    """
    Replays routing for a specific understood signal by ID.

    Fetches the understood_signal from Supabase, re-validates its contract,
    and re-dispatches. Previous signal_routes rows are preserved — new rows
    are appended, maintaining full audit history.

    Usage:
        replay = ReplayRouter()
        result = replay.replay(
            understood_signal_id="some-uuid",
            supabase_client=client,
        )
    """

    def __init__(self):
        self._router = SignalRouter()
        self._dispatcher = ContractDispatcher()

    def replay(
        self,
        understood_signal_id: str,
        supabase_client: Any,
    ) -> ReplayResult:
        """
        Replay routing for a specific understood signal.

        Args:
            understood_signal_id: UUID of the understood_signals record to replay.
            supabase_client: Authenticated Supabase client.

        Returns:
            ReplayResult with dispatch outcome.
        """
        logger.info(f"ReplayRouter: replaying signal {understood_signal_id}")

        # 1. Fetch understood_signal from Supabase
        understood_signal = self._fetch_understood_signal(
            understood_signal_id, supabase_client
        )

        if understood_signal is None:
            logger.error(
                f"ReplayRouter: signal {understood_signal_id} not found in understood_signals"
            )
            return ReplayResult(
                understood_signal_id=understood_signal_id,
                found=False,
                error=f"understood_signal {understood_signal_id} not found",
            )

        # 2. Route (validate + resolve)
        route_decision = self._router.route(understood_signal)

        # 3. Dispatch
        dispatch_result = self._dispatcher.dispatch(
            route_decision=route_decision,
            supabase_client=supabase_client,
        )

        logger.info(
            f"ReplayRouter: replay complete for {understood_signal_id} | "
            f"status={dispatch_result.overall_status} | "
            f"routes={dispatch_result.total_routes} | "
            f"completed={dispatch_result.completed}"
        )

        return ReplayResult(
            understood_signal_id=understood_signal_id,
            found=True,
            dispatch_result=dispatch_result,
        )

    def _fetch_understood_signal(
        self,
        understood_signal_id: str,
        supabase_client: Any,
    ) -> dict | None:
        """Fetch a single understood_signal record from Supabase by ID."""
        try:
            response = (
                supabase_client
                .table("understood_signals")
                .select("*")
                .eq("id", understood_signal_id)
                .limit(1)
                .execute()
            )
            rows = response.data
            if rows:
                return rows[0]
            return None
        except Exception as e:
            logger.error(
                f"ReplayRouter: failed to fetch signal {understood_signal_id}: {e}"
            )
            return None
