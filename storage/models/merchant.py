# storage/models/merchant.py

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class Merchant(Base):
    """
    Canonical merchant registry. Pre-seeded at startup and grown from observed transactions.
    The Financial Agent resolves raw merchant strings from SUA contracts against this table.
    """
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    canonical_name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True,
        comment="The clean display name, e.g. 'Zomato'"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Expense category this merchant belongs to, e.g. 'FOOD_DINING'"
    )
    # All known string variants that appear in SMS / UPI messages
    aliases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="e.g. ['zomato', 'ZOMATO INDIA', 'ZMT', 'zomato.com']"
    )
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_trusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Trusted merchants get higher classification confidence"
    )
    is_seed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True = shipped with codebase; False = learned from transactions"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
