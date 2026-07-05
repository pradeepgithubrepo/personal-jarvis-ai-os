# src/agents/fyi/detector.py

import json
from loguru import logger

class FyiDetector:
    """
    Determines if an understood signal is suitable for FYI (awareness)
    or if it should be excluded (actionable tasks or canonical memory).
    """

    @staticmethod
    def should_process(signal) -> bool:
        contract = {}
        if signal.contract_json:
            try:
                contract = json.loads(signal.contract_json)
            except Exception:
                contract = signal.contract_json if isinstance(signal.contract_json, dict) else {}

        # 1. Reject list (Promotions, OTP, Marketing, etc.)
        text = f"{signal.summary} {signal.reason}".lower()
        reject_words = ["otp", "promotion", "advertisement", "spam", "marketing", "discount alert", "offer coupon", "win cash", "flat 50%"]
        if any(rw in text for rw in reject_words):
            return False

        # 2. Actionable tasks: if TodoAgent evaluate_actionability says it requires action, Todo Agent owns it.
        from services.todo_agent import TodoAgent
        act = TodoAgent.evaluate_actionability(signal.summary or "", signal.reason or "", contract)
        if act["requires_user_action"]:
            logger.info(f"FyiDetector: Ignoring signal {signal.id} - actionable task owned by Todo Agent.")
            return False

        return True
