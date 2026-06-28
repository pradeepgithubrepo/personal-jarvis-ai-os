# storage/models/salary_source.py

import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class SalarySource(Base):
    """
    Registry of income streams (employers / clients) for salary detection.
    One row per income stream. Built from Tier 3 candidate detection and confirmed by user.
    """
    __tablename__ = "salary_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    canonical_name: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="Human-readable employer name e.g. 'Tech Mahindra Limited'"
    )
    # All SMS/NEFT sender strings observed for this employer
    aliases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="e.g. ['TECH MAHINDRA', 'TML', 'AD-SBIPSG-T']"
    )
    employment_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="salaried",
        comment="salaried | freelance | contract | pension"
    )
    expected_day_of_month: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Day salary typically arrives, e.g. 1 for 1st of month"
    )
    day_tolerance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3,
        comment="±N days variance allowed"
    )
    expected_amount: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Last known salary amount"
    )
    amount_tolerance_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.10,
        comment="Acceptable variance as a fraction, e.g. 0.10 = ±10%"
    )
    source_bank_aliases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Sender aliases specific to this employer's bank"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="False = candidate pending user confirmation; True = confirmed"
    )
    pending_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    first_detected: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_seen: Mapped[date | None] = mapped_column(Date, nullable=True)
    # JSON list of {month, amount, day, confidence} dicts
    detection_history: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
