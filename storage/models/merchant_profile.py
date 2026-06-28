# storage/models/merchant_profile.py

import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class MerchantProfile(Base):
    """
    Rolling spend profile per merchant. Updated by the Financial Agent on each transaction.
    Tracks lifetime and recent spend for merchant intelligence.
    """
    __tablename__ = "merchant_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    lifetime_spend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_transaction_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visit_count_last_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visit_count_last_90d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_transaction_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
