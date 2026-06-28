# storage/models/todo_item.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class TodoItem(Base):
    """
    Stateful action database representing user tasks and obligations.
    """
    __tablename__ = "todo_items"

    todo_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    title: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    category: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="FINANCIAL | MEDICAL | EDUCATION | TRAVEL | HOUSEHOLD | WORK | SUBSCRIPTION | INSURANCE | VEHICLE | GENERAL"
    )

    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MEDIUM",
        comment="CRITICAL | HIGH | MEDIUM | LOW"
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="OPEN",
        comment="OPEN | IN_PROGRESS | WAITING | COMPLETED | CANCELLED | EXPIRED"
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    source_agent: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    source_reference: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Metadata details: {'signal_id': '...', 'fact_id': '...'}"
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
