# src/agents/daily_brief/prioritizer.py

class DailyBriefPrioritizer:
    """
    Handles ordering and prioritization of todo items, FYI events, and facts.
    Priority sequence: HIGH > MEDIUM > LOW.
    """

    PRIORITY_MAP = {
        "CRITICAL": 3,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    @classmethod
    def sort_by_importance(cls, items: list) -> list:
        """
        Sorts items based on their priority or importance fields.
        """
        def get_rank(item):
            # Check for different property names in different models
            priority_val = getattr(item, "priority", None) or getattr(item, "importance", None) or "MEDIUM"
            return cls.PRIORITY_MAP.get(priority_val.upper(), 2)

        return sorted(items, key=get_rank, reverse=True)
