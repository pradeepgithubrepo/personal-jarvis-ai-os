"""
tests/test_fyi_llm_reasoning.py

Unit tests to verify Lane 3 (Ambiguous Signals) reasoning and LLM categorization
in FyiAgent.
"""
import os
import unittest
from dotenv import load_dotenv

from src.agents.fyi.fyi_agent import FyiAgent


class TestFyiLlmReasoning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(dotenv_path)
        cls.gemini_key = os.environ.get("GEMINI_API_KEY")
        if not cls.gemini_key:
            raise unittest.SkipTest("GEMINI_API_KEY missing from environment, skipping live LLM test.")

    def setUp(self):
        self.agent = FyiAgent()

    def test_lane3_ambiguous_school_homework(self):
        msg = "Dear Parents, We will be having our POP (Parent orientation Program) on 10.7.2026 Friday morning 10 am. Attendance is compulsory."
        contract = {
            "task_name": "Parent Orientation Program reminder",
            "due_date": "2026-07-10"
        }
        
        res = self.agent._classify_and_route(msg, contract)
        
        # Verify classification details
        self.assertIn(res["processing_path"], ["LLM_GEMINI", "LLM_CEREBRAS", "LLM_LOCAL"])
        self.assertEqual(res["category"], "FAMILY_SCHOOL")
        self.assertIn(res["importance_level"], ["HIGH", "CRITICAL"])
        self.assertIsNotNone(res["title"])
        self.assertIsNotNone(res["summary"])
        self.assertIsNone(res["timeline_group_id"]) # No structured PNR/order id, should be None


if __name__ == "__main__":
    unittest.main()
