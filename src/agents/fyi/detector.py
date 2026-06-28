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
        """
        Filters out:
        1. Actionable items (owned by Todo Agent)
        2. Canonical memory facts (owned by Fact Agent)
        """
        contract = {}
        if signal.contract_json:
            try:
                contract = json.loads(signal.contract_json)
            except Exception:
                contract = signal.contract_json if isinstance(signal.contract_json, dict) else {}

        classes = contract.get("classes", [])
        
        # 1. Actionable tasks: if ACTION class exists, Todo Agent owns it.
        if "ACTION" in classes:
            logger.info(f"FyiDetector: Ignoring signal {signal.id} - actionable task owned by Todo Agent.")
            return False

        # 2. Memory facts: if it is pure profile context extraction (e.g. spouse, child discovered)
        summary_lower = signal.summary.lower()
        if "discovered spouse" in summary_lower or "discovered child" in summary_lower or "user profile update" in summary_lower:
            logger.info(f"FyiDetector: Ignoring signal {signal.id} - canonical memory owned by Fact Agent.")
            return False

        return True
