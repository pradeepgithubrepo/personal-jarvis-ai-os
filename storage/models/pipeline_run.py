# storage/models/pipeline_run.py

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True
    )
    
    run_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # SCHEDULED, ADHOC, BACKFILL
    )
    
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # RUNNING, SUCCESS, FAILED
    )
    
    files_processed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    signals_processed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    todos_generated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    financial_events_generated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    fyi_generated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    facts_generated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    llm_calls: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    
    error_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True  # INGESTION_FAILURE, LLM_FAILURE, DATABASE_FAILURE, etc.
    )
