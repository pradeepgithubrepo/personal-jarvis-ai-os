# tests/test_context_provider.py

import sys
import os
import unittest

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.context_provider import ContextProvider


class TestContextProvider(unittest.TestCase):

    def test_load_context(self):
        context = ContextProvider.load_context()
        self.assertIsNotNone(context)
        self.assertIn("user", context)
        self.assertEqual(context["user"].get("name"), "Pradeep")
        self.assertIn("family", context)
        self.assertEqual(context["family"].get("spouse"), "Shobana")
        self.assertIn("Charan", context["family"].get("children", []))
        self.assertIn("Chinicka", context["family"].get("children", []))

    def test_get_context_prompt(self):
        prompt = ContextProvider.get_context_prompt()
        self.assertIsNotNone(prompt)
        
        # Verify the prompt contents match requirements
        expected_substrings = [
            "Jarvis User Context",
            "User: Pradeep",
            "Spouse:",
            "- Shobana",
            "Children:",
            "- Charan",
            "- Chinicka",
            "Family related messages are important.",
            "School related messages involving the children are high priority.",
            "Financial alerts and reminders are high priority.",
            "Badminton related information should be ignored unless explicitly actionable."
        ]
        
        for substring in expected_substrings:
            self.assertIn(substring, prompt)


if __name__ == "__main__":
    unittest.main()
