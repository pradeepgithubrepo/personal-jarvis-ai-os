# storage/models/financial_event.py

from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class FinancialEvent(Base):
    __tablename__ = "financial_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    
    amount: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )
    
    currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True
    )
    
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # debit, credit, renewal, etc.
    )
    
    payment_channel: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True  # UPI, Credit Card, Bank Transfer, Debit Card, etc.
    )
    
    paid_to: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    
    paid_from: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    
    transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    
    source_signal_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
