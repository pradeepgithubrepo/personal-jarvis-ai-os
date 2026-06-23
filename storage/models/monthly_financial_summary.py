# storage/models/monthly_financial_summary.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class MonthlyFinancialSummary(Base):
    __tablename__ = "monthly_financial_summary"

    summary_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    salary_cycle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("salary_cycles.salary_cycle_id", ondelete="CASCADE"),
        nullable=False
    )
    salary_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    total_credit: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    total_debit: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    net_savings: Mapped[float] = mapped_column(
        Float,
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
