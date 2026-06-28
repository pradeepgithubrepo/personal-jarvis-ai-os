# src/agents/fyi/agent.py

import json
from datetime import datetime
from loguru import logger
from sqlalchemy import select
from storage.models.understood_signal import UnderstoodSignal
from storage.models.fyi_event import FyiEvent
from src.agents.fyi.detector import FyiDetector
from src.agents.fyi.categorizer import FyiCategorizer
from src.agents.fyi.importance import FyiImportance
from src.agents.fyi.deduplicator import FyiDeduplicator
from src.agents.fyi.repository import FyiRepository

class FyiAgent:
    """
    Coordinates FYI processing pipeline.
    """

    @classmethod
    def ingest_candidate(cls, candidate: dict, db_session) -> str:
        """
        Ingests an FYI candidate dictionary, checks duplicates, and saves.
        """
        event_type = candidate.get("event_type")
        category = candidate.get("category", "SYSTEM")
        title = candidate.get("title")
        description = candidate.get("description")
        importance = candidate.get("importance", "MEDIUM")
        source_signal_id = candidate.get("source_signal_id")

        # 1. Deduplication
        existing = FyiDeduplicator.find_duplicate(event_type, title, db_session)
        if existing:
            logger.info(f"FyiAgent: Found duplicate event {existing.event_id}. Merging...")
            existing.duplicate_count += 1
            if description and description not in (existing.description or ""):
                existing.description = f"{existing.description or ''}\n{description}".strip()
            FyiRepository.update(existing, db_session)
            return existing.event_id

        # 2. Save new FYI event
        new_event = FyiEvent(
            event_type=event_type,
            category=category,
            title=title,
            description=description,
            importance=importance,
            status="UNREAD",
            source_signal_id=source_signal_id,
            duplicate_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        FyiRepository.save(new_event, db_session)
        return new_event.event_id

    @classmethod
    def process_all_understood_signals(cls, db_session) -> dict:
        """
        Main pipeline execution. Reads understood signals and generates FYI events.
        """
        logger.info("FyiAgent: Starting processing of understood signals...")
        stmt = select(UnderstoodSignal)
        signals = db_session.scalars(stmt).all()

        metrics = {
            "processed": 0,
            "fyi_created": 0,
            "failed": 0
        }

        for signal in signals:
            try:
                metrics["processed"] += 1

                # 1. Detection: Filter out actionable or memory-centric items
                if not FyiDetector.should_process(signal):
                    continue

                contract = {}
                if signal.contract_json:
                    try:
                        contract = json.loads(signal.contract_json)
                    except Exception:
                        contract = signal.contract_json if isinstance(signal.contract_json, dict) else {}

                # 2. Categorization
                category, event_type = FyiCategorizer.resolve(signal, contract)

                # 3. Importance Resolution
                importance = FyiImportance.resolve(event_type, signal.summary)

                # Ingest candidate
                candidate = {
                    "event_type": event_type,
                    "category": category,
                    "title": signal.summary,
                    "description": signal.reason,
                    "importance": importance,
                    "source_signal_id": signal.id
                }

                event_id = cls.ingest_candidate(candidate, db_session)
                if event_id:
                    metrics["fyi_created"] += 1

            except Exception as e:
                logger.error(f"FyiAgent: Failed to process signal {signal.id}: {e}")
                metrics["failed"] += 1

        logger.info(f"FyiAgent processing complete. Metrics: {metrics}")
        return metrics
