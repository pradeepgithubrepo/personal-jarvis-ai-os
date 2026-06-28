# storage/models/fyi_event.py

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class FyiEvent(Base):
    """
    Stateful database representing user FYI (awareness) events.
    """
    __tablename__ = "fyi_events"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="FINANCIAL | FAMILY | TRAVEL | SYSTEM"
    )

    title: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    importance: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEDIUM",
        comment="LOW | MEDIUM | HIGH"
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNREAD",
        comment="UNREAD | READ | ARCHIVED"
    )

    source_signal_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )

    duplicate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
