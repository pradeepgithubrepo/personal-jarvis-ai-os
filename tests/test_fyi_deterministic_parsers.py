"""
tests/test_fyi_deterministic_parsers.py

Unit tests to verify Lane 1 (STRUCTURED), Lane 2 (RULE_BASED), and Lane 2.5 (Short Bypass)
pre-classification, category mapping, and importance levels in FyiAgent.
"""
import unittest
from src.agents.fyi.fyi_agent import FyiAgent


class TestFyiDeterministicParsers(unittest.TestCase):
    def setUp(self):
        self.agent = FyiAgent()

    def test_lane1_train_pnr(self):
        msg = "PNR-4941680424\nTrn:12634\nDep.Time-18:23 Hrs. Frm NCJ to TBM"
        contract = {"type_specific": {"departure_time": "2026-05-04T18:23:00Z"}}
        
        res = self.agent._classify_and_route(msg, contract)
        self.assertEqual(res["processing_path"], "STRUCTURED")
        self.assertEqual(res["category"], "TRAVEL")
        self.assertEqual(res["importance_level"], "MEDIUM")
        self.assertEqual(res["timeline_group_id"], "train-4941680424")

    def test_lane1_service_ticket(self):
        msg = "Dear Customer, service engineer is at door step for Request No.JS-260701100851586"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "STRUCTURED")
        self.assertEqual(res["category"], "TRAVEL")
        self.assertEqual(res["importance_level"], "MEDIUM")
        self.assertEqual(res["timeline_group_id"], "service-js-260701100851586")

    def test_lane1_claim_settlement(self):
        msg = "We have processed claim 50485973 for policy. AXISCN1356798563"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "STRUCTURED")
        self.assertEqual(res["category"], "FINANCE_INSURANCE")
        self.assertEqual(res["importance_level"], "HIGH")
        self.assertEqual(res["timeline_group_id"], "claim-50485973")

    def test_lane1_locker_operation(self):
        msg = "Your Locker No SF02-00097 operated on 10-06-2026 at 14:32"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "STRUCTURED")
        self.assertEqual(res["category"], "SECURITY_ALERT")
        self.assertEqual(res["importance_level"], "CRITICAL")
        self.assertEqual(res["timeline_group_id"], "locker-sf02-00097")

    def test_lane1_order_shipped(self):
        msg = "Your order #391307 from Tru Hair has been shipped!"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "STRUCTURED")
        self.assertEqual(res["category"], "ORDER_TRACKING")
        self.assertEqual(res["importance_level"], "MEDIUM")
        self.assertEqual(res["timeline_group_id"], "order-391307")

    def test_lane2_survey_feedback(self):
        msg = "Thank you for choosing Livpure. Please provide your feedback at links..."
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "RULE_BASED")
        self.assertEqual(res["category"], "GENERAL")
        self.assertEqual(res["importance_level"], "LOW")

    def test_lane2_maintenance_alert(self):
        msg = "EPFO consolidation maintenance: services temporarily unavailable on 10-Jul"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "RULE_BASED")
        self.assertEqual(res["category"], "UTILITY_INFO")
        self.assertEqual(res["importance_level"], "MEDIUM")

    def test_lane1_amazon_order(self):
        msg = "406-8472581-9792369 is on the way.\nArriving in 7 mins"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "STRUCTURED")
        self.assertEqual(res["category"], "ORDER_TRACKING")
        self.assertEqual(res["importance_level"], "MEDIUM")
        self.assertEqual(res["timeline_group_id"], "order-406-8472581-9792369")

    def test_lane2_5_photo_media(self):
        msg = "📷 Photo"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "RULE_BASED")
        self.assertEqual(res["category"], "GENERAL")
        self.assertEqual(res["importance_level"], "EPHEMERAL")

    def test_lane2_5_short_transit(self):
        msg = "Reached home"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "RULE_BASED")
        self.assertEqual(res["category"], "TRAVEL")
        self.assertEqual(res["importance_level"], "EPHEMERAL")

    def test_lane2_5_short_chat(self):
        msg = "Have food"
        res = self.agent._classify_and_route(msg, {})
        self.assertEqual(res["processing_path"], "RULE_BASED")
        self.assertEqual(res["category"], "GENERAL")
        self.assertEqual(res["importance_level"], "EPHEMERAL")


if __name__ == "__main__":
    unittest.main()
