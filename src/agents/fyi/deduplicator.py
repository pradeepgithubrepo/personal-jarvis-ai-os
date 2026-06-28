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
        # Match within a 24-hour window
        limit_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(FyiEvent).where(
            and_(
                FyiEvent.event_type == event_type,
                FyiEvent.created_at >= limit_time
            )
        )
        candidates = db_session.scalars(stmt).all()

        norm_title = "".join(title.lower().split())
        for event in candidates:
            norm_event_title = "".join(event.title.lower().split())
            if norm_title == norm_event_title:
                return event

        return None
