# storage/models/understood_signal.py

from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer,
    Float,
    Boolean
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)
from storage.models.base import Base


class UnderstoodSignal(Base):
    __tablename__ = "understood_signals"

    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True
    )
    
    qualified_signal_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    
    raw_signal_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    signal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    importance: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    
    processing_path: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    
    llm_model_used: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    contract_json: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
