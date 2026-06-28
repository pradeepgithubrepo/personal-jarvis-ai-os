# storage/models/salary_event.py

import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class SalaryEvent(Base):
    """
    A detected salary credit. One row per monthly salary receipt.
    """
    __tablename__ = "salary_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    financial_event_id: Mapped[int] = mapped_column(
        ForeignKey("financial_events.id", ondelete="CASCADE"), nullable=False
    )
    salary_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("salary_sources.id", ondelete="SET NULL"), nullable=True,
        comment="Null if detected by keyword (Tier 1) and no source registered yet"
    )
    detected_employer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gross_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    salary_month: Mapped[date] = mapped_column(
        Date, nullable=False, comment="First day of the month this salary covers"
    )
    detection_method: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="keyword | registry_match | pattern | amount_match | unclassified"
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
