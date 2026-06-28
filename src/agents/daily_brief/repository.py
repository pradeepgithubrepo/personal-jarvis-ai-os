# src/agents/daily_brief/repository.py

from storage.models.daily_brief import DailyBrief
from services.supabase_repo import SupabaseRepo

class DailyBriefRepository:
    """
    Handles local SQLite database writes and replication updates to remote Supabase tables.
    """

    @staticmethod
    def save(brief: DailyBrief, db_session) -> str:
        db_session.add(brief)
        db_session.commit()
        
        # Mirror to Supabase
        SupabaseRepo.store_daily_brief(
            brief_id=brief.brief_id,
            brief_type=brief.brief_type,
            generated_at=brief.generated_at,
            content=brief.content,
            todo_count=brief.todo_count,
            fyi_count=brief.fyi_count,
            fact_count=brief.fact_count
        )
        return brief.brief_id
