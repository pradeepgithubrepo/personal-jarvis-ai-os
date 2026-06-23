# storage/models/monthly_category_spend.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class MonthlyCategorySpend(Base):
    __tablename__ = "monthly_category_spend"

    entry_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    month_key: Mapped[str] = mapped_column(
        String(7),
        nullable=False
    )
    category_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint("month_key", "category_name", name="uq_month_category"),
    )
