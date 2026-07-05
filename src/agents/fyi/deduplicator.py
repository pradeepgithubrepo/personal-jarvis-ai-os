# src/agents/fyi/deduplicator.py

from datetime import datetime, timedelta
from sqlalchemy import select, and_
from storage.models.fyi_event import FyiEvent

class FyiDeduplicator:
    """
    Deduplicates FYI events within a 24-hour window using event_type,
    created_at range, and normalized title comparison.
    """

    @staticmethod
    def find_duplicate(event_type: str, title: str, db_session) -> FyiEvent | None:
        limit_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(FyiEvent).where(
            and_(
                FyiEvent.event_type == event_type,
                FyiEvent.created_at >= limit_time
            )
        )
        candidates = db_session.scalars(stmt).all()

        title_words = set(title.lower().replace(",", " ").replace(".", " ").split())
        stop_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "from", "with", "by", "is", "was", "are", "were"}
        title_words = title_words - stop_words

        for event in candidates:
            event_words = set(event.title.lower().replace(",", " ").replace(".", " ").split()) - stop_words
            common_words = title_words.intersection(event_words)
            if common_words:
                overlap = len(common_words) / max(1, min(len(title_words), len(event_words)))
                if overlap >= 0.3:
                    return event

        return None
