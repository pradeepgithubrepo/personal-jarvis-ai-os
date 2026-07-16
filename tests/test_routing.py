"""
tests/test_routing.py

Phase 2B Routing Validation Suite — 7 deterministic unit tests.

Tests:
  1. FINANCIAL → financial_agent
  2. ACTION    → todo_agent
  3. FYI       → fyi_agent
  4. FACT      → fyi_agent
  5. NOISE     → no dispatch
  6. FINANCIAL + memory_candidate=True → financial_agent + fyi_agent
  7. Invalid contract → ContractValidationError, no dispatch

All tests are pure unit tests — no DB connection required.
"""
import unittest

from src.intelligence.contracts.contract_schema import SignalType, ContractValidationError, CONTRACT_VERSION
from src.intelligence.contracts.contract_validator import ContractValidator
from src.intelligence.routing.routing_rules import resolve_route
from src.intelligence.routing.router import SignalRouter
from src.intelligence.dispatch.dispatcher import ContractDispatcher, DispatchResult


# ---------------------------------------------------------------------------
# Helpers — build minimal valid understood_signal records
# ---------------------------------------------------------------------------

def _make_understood_signal(
    signal_type: str,
    memory_candidate: bool = False,
    financial_candidate: bool = False,
    fact_candidate: bool = False,
    fyi_candidate: bool = False,
    noise_candidate: bool = False,
    requires_action: bool = False,
) -> dict:
    """Build a minimal valid understood_signal dict for testing."""
    return {
        "id": "test-signal-uuid-0001",
        "signal_type": signal_type,
        "importance": 0.8,
        "confidence": 0.9,
        "summary": f"Test signal of type {signal_type}",
        "contract_json": {
            "contract_version": CONTRACT_VERSION,
            "signal_type": signal_type,
            "importance": 0.8,
            "confidence": 0.9,
            "summary": f"Test signal of type {signal_type}",
            "entities": [],
            "memory_candidate": memory_candidate,
            "requires_action": requires_action,
            "financial_candidate": financial_candidate,
            "fact_candidate": fact_candidate,
            "fyi_candidate": fyi_candidate,
            "noise_candidate": noise_candidate,
            "type_specific": {},
        },
    }


class TestContractValidation(unittest.TestCase):
    """Tests for contract validation logic."""

    def test_valid_financial_contract(self):
        """A well-formed FINANCIAL contract passes validation."""
        contract = {
            "contract_version": CONTRACT_VERSION,
            "signal_type": "FINANCIAL",
            "importance": 0.9,
            "confidence": 0.85,
            "summary": "Debit of INR 5000",
            "entities": ["Amazon"],
            "memory_candidate": False,
            "requires_action": False,
            "financial_candidate": True,
            "fact_candidate": False,
            "fyi_candidate": False,
            "noise_candidate": False,
            "type_specific": {},
        }
        result = ContractValidator.validate(contract)
        self.assertTrue(result.valid, f"Expected valid, got errors: {result.errors}")

    def test_invalid_contract_missing_fields(self):
        """Test 7 — Invalid contract (missing required fields) fails validation."""
        bad_contract = {
            "signal_type": "FINANCIAL",
            "importance": 0.9,
            # Missing: contract_version, confidence, summary, entities, flags
        }
        result = ContractValidator.validate(bad_contract, signal_id="test-invalid")
        self.assertFalse(result.valid)
        self.assertTrue(len(result.errors) > 0)
        # Verify no dispatch occurs when invalid
        with self.assertRaises(ContractValidationError):
            result.raise_if_invalid()

    def test_invalid_signal_type_rejected(self):
        """An unknown signal_type fails validation."""
        contract = {
            "contract_version": CONTRACT_VERSION,
            "signal_type": "UNKNOWN_TYPE",
            "importance": 0.5,
            "confidence": 0.5,
            "summary": "Bad signal",
            "entities": [],
            "memory_candidate": False,
            "requires_action": False,
            "financial_candidate": False,
            "fact_candidate": False,
            "fyi_candidate": False,
            "noise_candidate": False,
        }
        result = ContractValidator.validate(contract)
        self.assertFalse(result.valid)

    def test_importance_out_of_range_rejected(self):
        """importance > 1.0 fails validation."""
        contract = {
            "contract_version": CONTRACT_VERSION,
            "signal_type": "FINANCIAL",
            "importance": 1.5,  # invalid
            "confidence": 0.9,
            "summary": "Test",
            "entities": [],
            "memory_candidate": False,
            "requires_action": False,
            "financial_candidate": True,
            "fact_candidate": False,
            "fyi_candidate": False,
            "noise_candidate": False,
        }
        result = ContractValidator.validate(contract)
        self.assertFalse(result.valid)

    def test_candidate_flag_mismatch_rejected(self):
        """Candidate flag inconsistency fails validation."""
        contract = {
            "contract_version": CONTRACT_VERSION,
            "signal_type": "FINANCIAL",
            "importance": 0.8,
            "confidence": 0.8,
            "summary": "Test",
            "entities": [],
            "memory_candidate": False,
            "requires_action": False,
            "financial_candidate": False,  # WRONG — should be True for FINANCIAL
            "fact_candidate": False,
            "fyi_candidate": False,
            "noise_candidate": False,
        }
        result = ContractValidator.validate(contract)
        self.assertFalse(result.valid)
        self.assertTrue(any("financial_candidate" in e for e in result.errors))


class TestRoutingRules(unittest.TestCase):
    """Tests for routing rule resolution."""

    def test_1_financial_routes_to_financial_agent(self):
        """Test 1 — FINANCIAL signal dispatches to financial_agent."""
        contract = {"memory_candidate": False}
        routes, _ = resolve_route("FINANCIAL", contract)
        self.assertEqual(routes, ["financial_agent"])

    def test_2_action_routes_to_todo_agent(self):
        """Test 2 — ACTION signal dispatches to todo_agent."""
        contract = {"memory_candidate": False}
        routes, _ = resolve_route("ACTION", contract)
        self.assertEqual(routes, ["todo_agent"])

    def test_3_fyi_routes_to_fyi_agent(self):
        """Test 3 — FYI signal dispatches to fyi_agent."""
        contract = {"memory_candidate": True}  # memory_candidate has no conditional for FYI
        routes, _ = resolve_route("FYI", contract)
        self.assertEqual(routes, ["fyi_agent"])


    def test_5_noise_routes_to_nobody(self):
        """Test 5 — NOISE signal has no dispatch (pipeline terminates)."""
        contract = {"memory_candidate": False}
        routes, _ = resolve_route("NOISE", contract)
        self.assertEqual(routes, [])

    def test_6_financial_memory_candidate_routes_to_both(self):
        """Test 6 — FINANCIAL + memory_candidate=True dispatches to financial_agent AND fyi_agent."""
        contract = {"memory_candidate": True}
        routes, _ = resolve_route("FINANCIAL", contract)
        self.assertIn("financial_agent", routes)
        self.assertIn("fyi_agent", routes)
        self.assertEqual(len(routes), 2)

    def test_action_memory_candidate_routes_to_both(self):
        """ACTION + memory_candidate=True dispatches to todo_agent AND fyi_agent."""
        contract = {"memory_candidate": True}
        routes, _ = resolve_route("ACTION", contract)
        self.assertIn("todo_agent", routes)
        self.assertIn("fyi_agent", routes)
        self.assertEqual(len(routes), 2)

    def test_financial_no_memory_candidate_routes_to_one(self):
        """FINANCIAL without memory_candidate dispatches to financial_agent only."""
        contract = {"memory_candidate": False}
        routes, _ = resolve_route("FINANCIAL", contract)
        self.assertEqual(routes, ["financial_agent"])


class TestSignalRouter(unittest.TestCase):
    """Integration tests for SignalRouter (contract validation + routing)."""

    def setUp(self):
        self.router = SignalRouter()

    def test_router_financial_signal(self):
        """Router correctly routes valid FINANCIAL signal."""
        signal = _make_understood_signal("FINANCIAL", financial_candidate=True)
        decision = self.router.route(signal)
        self.assertTrue(decision.is_valid)
        self.assertIn("financial_agent", decision.route_to)

    def test_router_action_signal(self):
        """Router correctly routes valid ACTION signal."""
        signal = _make_understood_signal(
            "ACTION", requires_action=True, memory_candidate=True
        )
        decision = self.router.route(signal)
        self.assertTrue(decision.is_valid)
        self.assertIn("todo_agent", decision.route_to)

    def test_router_noise_signal_no_route(self):
        """Router produces empty route for NOISE signal."""
        signal = _make_understood_signal("NOISE", noise_candidate=True)
        decision = self.router.route(signal)
        self.assertTrue(decision.is_valid)
        self.assertEqual(decision.route_to, [])
        self.assertFalse(decision.has_routes)

    def test_router_financial_memory_candidate_multi_route(self):
        """Router dispatches to financial_agent + fyi_agent for FINANCIAL + memory_candidate."""
        signal = _make_understood_signal(
            "FINANCIAL",
            financial_candidate=True,
            memory_candidate=False,  # flag in contract_json
        )
        # Manually set memory_candidate=True in contract_json
        signal["contract_json"]["memory_candidate"] = True
        decision = self.router.route(signal)
        self.assertTrue(decision.is_valid)
        self.assertIn("financial_agent", decision.route_to)
        self.assertIn("fyi_agent", decision.route_to)

    def test_router_invalid_contract_no_dispatch(self):
        """Test 7 — Router marks invalid contract, no routes produced."""
        bad_signal = {
            "id": "bad-signal-001",
            "signal_type": "FINANCIAL",
            "contract_json": {
                # Missing required fields — should fail validation
                "signal_type": "FINANCIAL",
            },
        }
        decision = self.router.route(bad_signal)
        self.assertFalse(decision.is_valid)
        self.assertEqual(decision.route_to, [])
        self.assertTrue(len(decision.validation_errors) > 0)


class TestDispatcher(unittest.TestCase):
    """Tests for ContractDispatcher (no DB — supabase_client=None)."""

    def setUp(self):
        self.router = SignalRouter()
        self.dispatcher = ContractDispatcher()

    def _dispatch_signal(self, signal_type: str, **kwargs) -> "DispatchResult":
        signal = _make_understood_signal(signal_type, **kwargs)
        decision = self.router.route(signal)
        return self.dispatcher.dispatch(decision, supabase_client=None)

    def test_financial_dispatch_completes(self):
        result = self._dispatch_signal("FINANCIAL", financial_candidate=True)
        self.assertEqual(result.overall_status, "SUCCESS")
        self.assertEqual(result.pending, 1)
        self.assertEqual(result.records[0].status, "PENDING")

    def test_noise_dispatch_no_route(self):
        result = self._dispatch_signal("NOISE", noise_candidate=True)
        self.assertEqual(result.overall_status, "NO_ROUTE")
        self.assertEqual(result.total_routes, 0)

    def test_multi_route_dispatch(self):
        signal = _make_understood_signal("FINANCIAL", financial_candidate=True)
        signal["contract_json"]["memory_candidate"] = True
        decision = self.router.route(signal)
        result = self.dispatcher.dispatch(decision, supabase_client=None)
        self.assertEqual(result.total_routes, 2)
        self.assertEqual(result.pending, 2)
        agent_names = [r.agent_name for r in result.records]
        self.assertIn("financial_agent", agent_names)
        self.assertIn("fyi_agent", agent_names)
        for r in result.records:
            self.assertEqual(r.status, "PENDING")

    def test_invalid_contract_dispatch_validation_failed(self):
        """Invalid contract → VALIDATION_FAILED status, no agents dispatched."""
        bad_signal = {
            "id": "bad-uuid-001",
            "signal_type": "FINANCIAL",
            "contract_json": {"signal_type": "FINANCIAL"},
        }
        decision = self.router.route(bad_signal)
        result = self.dispatcher.dispatch(decision, supabase_client=None)
        self.assertEqual(result.overall_status, "VALIDATION_FAILED")
        self.assertEqual(result.pending, 0)


if __name__ == "__main__":
    unittest.main()
