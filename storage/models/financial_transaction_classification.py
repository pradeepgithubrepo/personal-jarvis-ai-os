# storage/models/financial_transaction_classification.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class FinancialTransactionClassification(Base):
    __tablename__ = "financial_transaction_classification"

    transaction_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    financial_event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("financial_events.id", ondelete="CASCADE"),
        nullable=False
    )
    classification: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
