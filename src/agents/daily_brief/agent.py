# src/agents/daily_brief/agent.py

from datetime import datetime, time
from sqlalchemy import select, and_, or_
from loguru import logger
from storage.models.todo_item import TodoItem
from storage.models.fyi_event import FyiEvent
from storage.models.fact import Fact
from storage.models.daily_brief import DailyBrief
from src.agents.daily_brief.builder import DailyBriefBuilder
from src.agents.daily_brief.repository import DailyBriefRepository

class DailyBriefAgent:
    """
    Orchestrates the loading, prioritization, text generation, and persistence of briefs.
    """

    @classmethod
    def generate_morning_brief(cls, db_session) -> str:
        """
        Gathers active obligations, unread FYIs, and verified facts to compile a Morning Brief.
        """
        logger.info("DailyBriefAgent: Compiling Morning Brief...")

        # 1. Load Todos: OPEN, IN_PROGRESS (meaning not COMPLETED/CANCELLED/RETIRED)
        stmt_todos = select(TodoItem).where(
            or_(
                TodoItem.status == "OPEN",
                TodoItem.status == "IN_PROGRESS"
            )
        )
        todos = list(db_session.scalars(stmt_todos).all())

        # 2. Load FYIs: UNREAD, importance HIGH or MEDIUM (exclude ARCHIVED, READ, LOW)
        stmt_fyis = select(FyiEvent).where(
            and_(
                FyiEvent.status == "UNREAD",
                or_(FyiEvent.importance == "HIGH", FyiEvent.importance == "MEDIUM")
            )
        )
        fyis = list(db_session.scalars(stmt_fyis).all())

        # 3. Load Facts: VERIFIED, UNCONFIRMED
        stmt_facts = select(Fact).where(
            or_(
                Fact.status == "VERIFIED",
                Fact.status == "UNCONFIRMED"
            )
        )
        facts = list(db_session.scalars(stmt_facts).all())

        # 4. Build Brief Content
        content = DailyBriefBuilder.build_morning_brief(todos, fyis, facts)

        # 5. Persist Brief
        brief = DailyBrief(
            brief_type="MORNING",
            generated_at=datetime.utcnow(),
            content=content,
            todo_count=len(todos),
            fyi_count=len(fyis),
            fact_count=len(facts)
        )
        DailyBriefRepository.save(brief, db_session)
        logger.info(f"DailyBriefAgent: Morning Brief persisted. ID: {brief.brief_id}")

        return brief.brief_id

    @classmethod
    def generate_evening_brief(cls, db_session) -> str:
        """
        Gathers completed tasks, facts logged, and FYIs received today to compile an Evening Brief.
        """
        logger.info("DailyBriefAgent: Compiling Evening Brief...")
        today_start = datetime.combine(datetime.utcnow().date(), time.min)

        # 1. Load completed todos today
        stmt_todos = select(TodoItem).where(
            and_(
                TodoItem.status == "COMPLETED",
                TodoItem.updated_at >= today_start
            )
        )
        todos = list(db_session.scalars(stmt_todos).all())

        # 2. Load FYIs received today
        stmt_fyis = select(FyiEvent).where(
            FyiEvent.created_at >= today_start
        )
        fyis = list(db_session.scalars(stmt_fyis).all())

        # 3. Load facts created today
        stmt_facts = select(Fact).where(
            Fact.first_seen >= today_start
        )
        facts = list(db_session.scalars(stmt_facts).all())

        # 4. Build Brief Content
        content = DailyBriefBuilder.build_evening_brief(todos, fyis, facts)

        # 5. Persist Brief
        brief = DailyBrief(
            brief_type="EVENING",
            generated_at=datetime.utcnow(),
            content=content,
            todo_count=len(todos),
            fyi_count=len(fyis),
            fact_count=len(facts)
        )
        DailyBriefRepository.save(brief, db_session)
        logger.info(f"DailyBriefAgent: Evening Brief persisted. ID: {brief.brief_id}")

        return brief.brief_id
