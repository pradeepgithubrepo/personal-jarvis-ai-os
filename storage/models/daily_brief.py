# storage/models/daily_brief.py

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class DailyBrief(Base):
    """
    Stateful database representing Daily Brief summaries.
    """
    __tablename__ = "daily_briefs"

    brief_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    brief_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="MORNING | EVENING"
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    todo_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    fyi_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    fact_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
