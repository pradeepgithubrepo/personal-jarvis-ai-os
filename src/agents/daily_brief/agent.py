# src/agents/daily_brief/agent.py

import json
import time
import os
from datetime import datetime
from loguru import logger
from storage.models.daily_brief import DailyBrief
from src.agents.daily_brief.context_builder import DailyBriefContextBuilder
from src.agents.daily_brief.llm_renderer import DailyBriefLLMRenderer
from src.agents.daily_brief.repository import DailyBriefRepository

class DailyBriefAgent:
    """
    Orchestrates the loading, prioritization, text generation, and persistence of briefs.
    """

    @classmethod
    def _has_brief_for_date(cls, brief_type: str, target_date: datetime, db_session) -> str | None:
        from datetime import time
        from sqlalchemy import select, and_
        today_start = datetime.combine(target_date.date(), time.min)
        today_end = datetime.combine(target_date.date(), time.max)
        
        stmt = select(DailyBrief).where(
            and_(
                DailyBrief.brief_type == brief_type,
                DailyBrief.generated_at >= today_start,
                DailyBrief.generated_at <= today_end
            )
        )
        existing = db_session.scalars(stmt).first()
        if existing:
            return existing.brief_id
        return None

    @classmethod
    def generate_morning_brief(cls, db_session) -> str:
        """
        Gathers active obligations, unread FYIs, and verified facts to compile a Morning Brief.
        """
        target_date = datetime.utcnow()
        existing_id = cls._has_brief_for_date("MORNING", target_date, db_session)
        if existing_id:
            logger.info(f"DailyBriefAgent: MORNING brief already generated for {target_date.date()}. Skipping.")
            return existing_id

        logger.info("DailyBriefAgent: Compiling Morning Brief...")
        generation_started = datetime.utcnow().isoformat()

        # 1. Build Context
        context = DailyBriefContextBuilder.build_context(db_session, target_date)

        # 2. Render Brief Content via LLM (measure duration)
        start_time = time.perf_counter()
        content = DailyBriefLLMRenderer.render_brief(context, "MORNING")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        generation_completed = datetime.utcnow().isoformat()

        # 3. Add Quality Metadata and Structured Keys to payload
        context["generated_by"] = "llm"
        context["model"] = os.environ.get("LOCAL_MODEL", "qwen2.5:1.5b")
        context["generation_time_ms"] = duration_ms
        context["context_version"] = "v2"
        
        # V1.5 Generation Metrics
        context["generation_started"] = generation_started
        context["generation_completed"] = generation_completed
        context["generation_duration_ms"] = duration_ms
        context["model_used"] = os.environ.get("LOCAL_MODEL", "qwen2.5:1.5b")
        context["token_count"] = None

        # 4. Persist Brief
        brief = DailyBrief(
            brief_type="MORNING",
            generated_at=target_date,
            content=content,
            todo_count=len(context["today_tasks"]) + len(context["overdue_tasks"]),
            fyi_count=len(context["new_fyis"]),
            fact_count=len(context["new_facts"]),
            payload_json=json.dumps(context)
        )
        DailyBriefRepository.save(brief, db_session)
        logger.info(f"DailyBriefAgent: Morning Brief persisted. ID: {brief.brief_id}")

        return brief.brief_id

    @classmethod
    def generate_evening_brief(cls, db_session) -> str:
        """
        Gathers completed tasks, facts logged, and FYIs received today to compile an Evening Brief.
        """
        target_date = datetime.utcnow()
        existing_id = cls._has_brief_for_date("EVENING", target_date, db_session)
        if existing_id:
            logger.info(f"DailyBriefAgent: EVENING brief already generated for {target_date.date()}. Skipping.")
            return existing_id

        logger.info("DailyBriefAgent: Compiling Evening Brief...")
        generation_started = datetime.utcnow().isoformat()

        # 1. Build Context
        context = DailyBriefContextBuilder.build_context(db_session, target_date)

        # 2. Render Brief Content via LLM (measure duration)
        start_time = time.perf_counter()
        content = DailyBriefLLMRenderer.render_brief(context, "EVENING")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        generation_completed = datetime.utcnow().isoformat()

        # 3. Add Quality Metadata and Structured Keys to payload
        context["generated_by"] = "llm"
        context["model"] = os.environ.get("LOCAL_MODEL", "qwen2.5:1.5b")
        context["generation_time_ms"] = duration_ms
        context["context_version"] = "v2"
        
        # V1.5 Generation Metrics
        context["generation_started"] = generation_started
        context["generation_completed"] = generation_completed
        context["generation_duration_ms"] = duration_ms
        context["model_used"] = os.environ.get("LOCAL_MODEL", "qwen2.5:1.5b")
        context["token_count"] = None

        # 4. Persist Brief
        brief = DailyBrief(
            brief_type="EVENING",
            generated_at=target_date,
            content=content,
            todo_count=len(context["today_tasks"]) + len(context["overdue_tasks"]),
            fyi_count=len(context["new_fyis"]),
            fact_count=len(context["new_facts"]),
            payload_json=json.dumps(context)
        )
        DailyBriefRepository.save(brief, db_session)
        logger.info(f"DailyBriefAgent: Evening Brief persisted. ID: {brief.brief_id}")

        return brief.brief_id


