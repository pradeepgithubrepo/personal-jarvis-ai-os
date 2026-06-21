# storage/models/fyi_event.py

from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class FyiEvent(Base):
    __tablename__ = "fyi_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    
    fyi_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False  # delivery_notification, school_circular, travel_update, family_update, general_notification
    )
    
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    
    source_signal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
