# storage/models/transfer_pair.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Interval
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class TransferPair(Base):
    """
    Records a validated internal transfer pair (debit leg + credit leg).
    Created only when all 4 detection conditions are satisfied.
    """
    __tablename__ = "transfer_pairs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    debit_event_id: Mapped[int] = mapped_column(
        ForeignKey("financial_events.id", ondelete="CASCADE"), nullable=False
    )
    credit_event_id: Mapped[int] = mapped_column(
        ForeignKey("financial_events.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    transfer_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNKNOWN",
        comment="IMPS | NEFT | RTGS | UPI | YONO | UNKNOWN"
    )
    # Window used for detection (stored as seconds for SQLite compatibility)
    window_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
