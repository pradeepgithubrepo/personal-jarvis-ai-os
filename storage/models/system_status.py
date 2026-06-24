# storage/models/system_status.py

from datetime import datetime
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class SystemStatus(Base):
    __tablename__ = "system_status"

    system_name: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        default="jarvis_system"
    )
    
    current_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # IDLE, RUNNING, ERROR
    )
    
    last_successful_refresh: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    
    current_run_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
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
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
