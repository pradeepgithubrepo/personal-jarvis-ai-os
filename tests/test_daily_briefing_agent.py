"""
tests/test_daily_briefing_agent.py

Comprehensive Unit & Integration Test Suite for DailyBriefingAgent V1 (Signature 10/10 Experience).
"""
import datetime
import unittest
from unittest.mock import MagicMock, patch

from src.agents.daily_briefing.daily_briefing_agent import DailyBriefingAgent


class TestDailyBriefingAgent(unittest.TestCase):
    def setUp(self):
        self.agent = DailyBriefingAgent()
        self.mock_supabase = MagicMock()

    def test_agent_name_and_stub_process(self):
        self.assertEqual(self.agent.agent_name, "daily_briefing_agent")
        res = self.agent.process({})
        self.assertEqual(res.status, "COMPLETED")
        self.assertEqual(res.agent_name, "daily_briefing_agent")

    def test_is_noise_suppression(self):
        self.assertTrue(self.agent.is_noise("Media Received (Photo)"))
        self.assertTrue(self.agent.is_noise("Reached home"))
        self.assertTrue(self.agent.is_noise("Chat alert: hello"))
        self.assertTrue(self.agent.is_noise("Service Request Status update"))

        self.assertFalse(self.agent.is_noise("Livpure installation has been scheduled"))
        self.assertFalse(self.agent.is_noise("Pay SBI Card Bill"))

    def test_cross_section_deduplication(self):
        raw_briefing = {
            "title": "Good Morning",
            "day_status": {
                "status": "Busy",
                "color": "Amber",
                "reason": "Overdue bills and school program today.",
            },
            "overall_priority": "HIGH",
            "sections": [
                {
                    "type": "attention",
                    "title": "Needs Attention",
                    "items": [
                        "Pay SBI Card Bill overdue",
                        "Attend Little Millennium Parent Orientation Program today",
                    ],
                },
                {
                    "type": "lifecycle",
                    "title": "Upcoming Lifecycle Events",
                    "items": [
                        "Little Millennium Parent Orientation Program today",  # DUPLICATE! Should be stripped!
                        "Car Insurance Renewal due next week",
                    ],
                },
            ],
            "closing_message": "Today's priorities are clearing the overdue SBI card payment and attending the school orientation.",
        }

        clean = self.agent.validate_and_sanitize_briefing(raw_briefing, {})

        sections = {sec["type"]: sec["items"] for sec in clean["sections"]}

        self.assertIn("attention", sections)
        self.assertIn("lifecycle", sections)
        # Parent orientation should be in Attention, but stripped from Lifecycle!
        self.assertEqual(len(sections["attention"]), 2)
        self.assertEqual(len(sections["lifecycle"]), 1)
        self.assertEqual(sections["lifecycle"][0], "Car Insurance Renewal due next week")

    def test_conversational_finance_and_day_status(self):
        raw_briefing = {
            "title": "Good Morning",
            "day_status": {
                "status": "Action Required",
                "color": "Red",
                "reason": "Two overdue financial obligations.",
            },
            "overall_priority": "HIGH",
            "sections": [
                {
                    "type": "since_yesterday",
                    "title": "Since Yesterday",
                    "items": ["3 new tasks created", "1 payment completed"],
                },
                {
                    "type": "finance",
                    "title": "Financial Snapshot",
                    "items": [
                        "+₹109,424 (Income: ₹511K vs Expense: ₹401K)",  # Raw formula — should be stripped!
                        "Your cash flow remains healthy this month.",
                        "One significant investment transaction was recorded.",
                        "Electricity bill of ₹2,351 is due before July 30.",
                    ],
                },
            ],
            "closing_message": "Today's priorities are clearing overdue payments.",
        }

        clean = self.agent.validate_and_sanitize_briefing(raw_briefing, {})

        self.assertEqual(clean["day_status"]["status"], "Action Required")
        self.assertEqual(clean["day_status"]["color"], "Red")

        sections = {sec["type"]: sec["items"] for sec in clean["sections"]}

        # Raw formula stripped, remaining conversational insights kept
        self.assertNotIn("+₹109,424 (Income: ₹511K vs Expense: ₹401K)", sections["finance"])
        self.assertEqual(sections["finance"][0], "Your cash flow remains healthy this month.")

    @patch.object(DailyBriefingAgent, "fetch_trusted_context")
    def test_llm_fallback_execution(self, mock_fetch):
        mock_fetch.return_value = {
            "tasks": [{"id": "t1", "title": "Pay SBI Card Bill"}],
            "lifecycle_items": [],
            "information_items": [],
            "since_yesterday_metrics": {"new_tasks_created": 1, "payments_completed": 0, "new_info_items": 0},
        }

        def mock_ask(prompt, provider=None, model=None, options=None):
            if provider == "gemini":
                raise Exception("Gemini 429 Throttle Error")
            elif provider == "mistral":
                return """
                {
                  "title": "Good Morning",
                  "day_status": {
                    "status": "Busy",
                    "color": "Amber",
                    "reason": "One overdue credit card payment."
                  },
                  "overall_priority": "HIGH",
                  "sections": [
                    {
                      "type": "attention",
                      "title": "Needs Attention",
                      "items": ["Pay SBI credit card bill (22 days overdue)"]
                    }
                  ],
                  "closing_message": "Today's priority is settling the overdue SBI card bill."
                }
                """
            return "{}"

        self.agent.llm_client.ask = MagicMock(side_effect=mock_ask)

        mock_insert = MagicMock()
        mock_insert.insert.return_value.execute.return_value.data = [{"id": "b123"}]
        self.mock_supabase.table.return_value = mock_insert

        res = self.agent.generate_daily_briefing(self.mock_supabase, target_date=datetime.date(2026, 7, 21))

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["briefing_record"]["llm_provider"], "mistral")
        self.assertEqual(res["briefing_record"]["briefing_json"]["day_status"]["status"], "Busy")


if __name__ == "__main__":
    unittest.main()
