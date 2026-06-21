# storage/models/daily_brief.py

from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    
    date: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False  # YYYY-MM-DD
    )
    
    content_json: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
