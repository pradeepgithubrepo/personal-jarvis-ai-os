# storage/models/monthly_spending_summary.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class MonthlySpendingSummary(Base):
    __tablename__ = "monthly_spending_summary"

    summary_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    month_key: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        unique=True
    )
    total_spend: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    transaction_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
