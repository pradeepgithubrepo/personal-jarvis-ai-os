# src/agents/fyi/contracts.py

class FyiCandidate:
    """
    Candidate ingestion contract for FYI Agent.
    """
    def __init__(self, event_type: str, title: str, description: str, category: str, importance: str, source_signal_id: str):
        self.event_type = event_type
        self.title = title
        self.description = description
        self.category = category
        self.importance = importance
        self.source_signal_id = source_signal_id

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "importance": self.importance,
            "source_signal_id": self.source_signal_id
        }
