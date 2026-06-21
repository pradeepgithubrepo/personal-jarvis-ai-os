# storage/models/signal_classification.py

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class SignalClassification(Base):
    __tablename__ = "signal_classification"

    signal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # TODO, FINANCIAL, FYI, IGNORE
    
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False
    )
    
    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
