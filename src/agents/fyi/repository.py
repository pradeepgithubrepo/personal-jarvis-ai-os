# src/agents/fyi/repository.py

from datetime import datetime
from storage.models.fyi_event import FyiEvent
from services.supabase_repo import SupabaseRepo

class FyiRepository:
    """
    Handles local SQLite database writes and replication updates to remote Supabase tables.
    """

    @staticmethod
    def save(event: FyiEvent, db_session) -> str:
        db_session.add(event)
        db_session.commit()
        
        # Mirror to Supabase
        SupabaseRepo.store_fyi_event(
            event_id=event.event_id,
            event_type=event.event_type,
            category=event.category,
            title=event.title,
            description=event.description,
            importance=event.importance,
            status=event.status,
            source_signal_id=event.source_signal_id,
            duplicate_count=event.duplicate_count,
            created_at=event.created_at,
            updated_at=event.updated_at
        )
        return event.event_id

    @staticmethod
    def update(event: FyiEvent, db_session) -> str:
        event.updated_at = datetime.utcnow()
        db_session.commit()
        
        # Mirror to Supabase
        SupabaseRepo.store_fyi_event(
            event_id=event.event_id,
            event_type=event.event_type,
            category=event.category,
            title=event.title,
            description=event.description,
            importance=event.importance,
            status=event.status,
            source_signal_id=event.source_signal_id,
            duplicate_count=event.duplicate_count,
            created_at=event.created_at,
            updated_at=event.updated_at
        )
        return event.event_id
