# storage/models/qualified_signal.py

from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)
from storage.models.base import Base


class QualifiedSignal(Base):
    __tablename__ = "qualified_signals"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )
    
    signal_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    sender: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    
    qualification_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    
    qualification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    qualification_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
