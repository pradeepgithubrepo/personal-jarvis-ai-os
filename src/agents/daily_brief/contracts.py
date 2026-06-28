# src/agents/daily_brief/contracts.py

class DailyBriefContract:
    """
    Unified output contract representing the generated summary briefs.
    """
    def __init__(self, brief_id: str, brief_type: str, generated_at, content: str, todo_count: int, fyi_count: int, fact_count: int):
        self.brief_id = brief_id
        self.brief_type = brief_type
        self.generated_at = generated_at
        self.content = content
        self.todo_count = todo_count
        self.fyi_count = fyi_count
        self.fact_count = fact_count

    def to_dict(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "brief_type": self.brief_type,
            "generated_at": self.generated_at.isoformat() if hasattr(self.generated_at, "isoformat") else str(self.generated_at),
            "content": self.content,
            "todo_count": self.todo_count,
            "fyi_count": self.fyi_count,
            "fact_count": self.fact_count
        }
